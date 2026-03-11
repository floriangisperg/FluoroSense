import streamlit as st

# Page config must be first
st.set_page_config(
    layout="wide",
    page_title="Time Series Measurement",
    page_icon="⏳"
)

from styles import apply_dark_lab_theme, get_plotly_dark_template, EMISSION_PALETTE

# Apply theme after page config
apply_dark_lab_theme()

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from scipy.integrate import simpson
from scipy.optimize import curve_fit
from scipy.stats import t
import io
from io import StringIO
from io import BytesIO
from openpyxl import Workbook
from openpyxl.writer.excel import save_workbook
from tempfile import NamedTemporaryFile
from dataclasses import dataclass, field
from typing import Dict, Optional, List
import colorsys
import hashlib
import json

def compute_content_hash(file_content: bytes) -> str:
    """Compute SHA256 hash of file content for caching"""
    return hashlib.sha256(file_content).hexdigest()[:16]

def validate_wavelength_grid(runs: Dict[str, 'TimeSeriesRun']) -> tuple:
    """
    Validate that all runs have consistent wavelength grids.
    Returns (is_valid, warning_message, mismatched_files)
    """
    if len(runs) <= 1:
        return True, None, []

    # Get reference grid from first run
    reference_run = list(runs.values())[0]
    if reference_run.raw_df.empty:
        return True, None, []

    reference_grid = np.array(reference_run.raw_df.index.values, dtype=float)
    mismatched = []

    for run_id, run in runs.items():
        if run.raw_df.empty:
            continue
        current_grid = np.array(run.raw_df.index.values, dtype=float)

        # Check if grids match (allow small tolerance for floating point)
        if len(current_grid) != len(reference_grid):
            mismatched.append(run.file_name)
        elif not np.allclose(current_grid, reference_grid, rtol=1e-5):
            mismatched.append(run.file_name)

    if mismatched:
        warning = f"⚠️ **Wavelength grid mismatch detected!** The following files have different wavelength grids and may produce inconsistent results:\n\n"
        for f in mismatched:
            warning += f"- `{f}`\n"
        warning += "\nConsider excluding these files or processing separately."
        return False, warning, mismatched

    return True, None, []

@dataclass
class TimeSeriesRun:
    """Container for a single time series run"""
    run_id: str
    file_name: str
    header: dict
    raw_df: pd.DataFrame
    content_hash: str = ""
    processed_df: Optional[pd.DataFrame] = None
    blank_config: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    status: str = 'pending'


# plot settings - Dark Lab theme
width = 1200
height = 600
download_width = 1200
download_height = 600
download_text_scale = 1

# Get dark template
dark_template = get_plotly_dark_template()

config = {
    'displaylogo': False,
    'toImageButtonOptions': {
        'format': 'svg',
        'filename': 'fluorosense_plot',
        'height': download_height,
        'width': download_width,
        'scale': download_text_scale
    },
    'modeBarButtonsToAdd': [
        'hoverclosest', 'hovercompare', 'togglehover', 'togglespikelines',
        'v1hovermode', 'drawline', 'drawopenpath', 'drawclosedpath',
        'drawcircle', 'drawrect', 'eraseshape'
    ],
    'displayModeBar': True
}

@st.cache_data
def upload_jasco_rawdata(uploaded_file):
    """Parse Jasco raw data files"""
    header = {}
    xydata = []
    extended_info = {}

    lines = uploaded_file.readlines()
    mode = 'header'
    data_started = False
    data_ended = False

    for line in lines:
        line = line.decode().strip()

        if line.startswith('XYDATA'):
            mode = 'data'
            data_started = False
            continue

        if line.startswith('##### Extended Information'):
            mode = 'extended'
            data_ended = True
            continue

        if mode == 'header':
            if ',' in line:
                parts = line.split(',', 1)
                if len(parts) == 2:
                    key, value = parts
                    header[key] = value.rstrip(',')

        elif mode == 'data':
            if not line or line.isspace():
                continue
            if line.startswith('#####'):
                mode = 'extended'
                data_ended = True
                continue
            if not data_started and ',' in line and not line.startswith('#'):
                data_started = True
                xydata.append(line.split(','))
                continue
            if data_started and not data_ended:
                fields = line.split(',')
                if len(fields) >= 2:
                    xydata.append(fields)

        elif mode == 'extended':
            if ',' in line:
                parts = line.split(',', 1)
                if len(parts) == 2:
                    key, value = parts
                    extended_info[key.strip()] = value.strip()

    if xydata and len(xydata) > 1:
        try:
            df = pd.DataFrame(xydata[1:], columns=xydata[0])
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            try:
                if '' in df.columns:
                    df.set_index('', inplace=True)
                elif df.columns[0].strip() == '':
                    df.set_index(df.columns[0], inplace=True)
            except:
                pass
            df = df.dropna(how='all')
        except Exception as e:
            st.error(f"Error processing data: {str(e)}")
            df = pd.DataFrame()
    else:
        df = pd.DataFrame()

    return header, df, extended_info


def subtract_blank_from_time_series(df, blank_method='timepoint', blank_timepoint=None, blank_start=None, blank_end=None):
    """Subtract blank spectrum from time series"""
    result_df = df.copy()

    try:
        if blank_method == 'timepoint' and blank_timepoint:
            if blank_timepoint in result_df.columns:
                blank_spectrum = result_df[blank_timepoint]
            else:
                return df
        elif blank_method == 'average' and blank_start and blank_end:
            column_options = df.columns.tolist()
            try:
                start_idx = column_options.index(blank_start)
                end_idx = column_options.index(blank_end)
                if start_idx > end_idx:
                    start_idx, end_idx = end_idx, start_idx
                cols_between = column_options[start_idx:(end_idx + 1)]
                if cols_between:
                    blank_spectrum = result_df[cols_between].mean(axis=1)
                else:
                    return df
            except:
                return df
        else:
            return df

        for col in result_df.columns:
            result_df[col] = result_df[col] - blank_spectrum

        st.session_state['blank_subtraction_applied'] = True
        return result_df
    except:
        return df


def blank_subtraction_ui(df):
    """UI for blank subtraction"""
    st.sidebar.markdown("## Blank Subtraction")
    use_blank = st.sidebar.checkbox("Apply Blank Subtraction", False)

    if not use_blank:
        st.session_state['blank_subtraction_applied'] = False
        return df

    column_options = df.columns.tolist()
    if not column_options:
        return df

    blank_method = st.sidebar.radio("Method", ["Single Timepoint", "Average of Range"], index=0)

    if blank_method == "Single Timepoint":
        blank_timepoint = st.sidebar.selectbox("Select blank timepoint", column_options, index=0)
        result_df = subtract_blank_from_time_series(df, blank_method='timepoint', blank_timepoint=blank_timepoint)
    else:
        col1, col2 = st.sidebar.columns(2)
        with col1:
            blank_start = st.selectbox("Start", column_options, index=0)
        with col2:
            start_index = column_options.index(blank_start)
            blank_end = st.selectbox("End", column_options, index=min(start_index + 3, len(column_options) - 1))
        result_df = subtract_blank_from_time_series(df, blank_method='average', blank_start=blank_start, blank_end=blank_end)

    if st.session_state.get('blank_subtraction_applied', False):
        st.sidebar.success("Blank applied!")

    return result_df


def batch_blank_subtraction_ui(runs):
    """UI for batch blank subtraction"""
    st.sidebar.markdown("## Batch Blank Subtraction")

    if not runs:
        st.sidebar.info("Upload files first")
        return runs

    # Status overview
    status_text = []
    for run_id, run in runs.items():
        status_text.append(f"{'✓' if run.blank_config.get('applied') else '○'} {run.file_name}")
    st.sidebar.markdown("**Status:**\n" + "\n".join(status_text))

    run_options = {run.file_name: run_id for run_id, run in runs.items()}
    selected_file = st.sidebar.selectbox("Select file", list(run_options.keys()))

    if not selected_file:
        return runs

    selected_run_id = run_options[selected_file]
    selected_run = runs[selected_run_id]

    use_blank = st.sidebar.checkbox("Apply Blank", value=selected_run.blank_config.get('enabled', False), key=f"batch_use_blank_{selected_run_id}")

    if use_blank:
        df = selected_run.raw_df
        column_options = df.columns.tolist()

        if column_options:
            blank_method = st.sidebar.radio("Method", ["Single Timepoint", "Average of Range"], index=0, key=f"batch_method_{selected_run_id}")

            if blank_method == "Single Timepoint":
                blank_timepoint = st.sidebar.selectbox("Timepoint", column_options, index=0, key=f"batch_tp_{selected_run_id}")
                if st.sidebar.button("Apply", key=f"batch_apply_{selected_run_id}"):
                    result_df = subtract_blank_from_time_series(df, blank_method='timepoint', blank_timepoint=blank_timepoint)
                    selected_run.processed_df = result_df
                    selected_run.blank_config = {'enabled': True, 'applied': True, 'method': 'timepoint', 'timepoint': blank_timepoint}
                    runs[selected_run_id] = process_single_run(selected_run)
            else:
                col1, col2 = st.sidebar.columns(2)
                with col1:
                    blank_start = st.sidebar.selectbox("Start", column_options, index=0, key=f"batch_start_{selected_run_id}")
                with col2:
                    blank_end = st.sidebar.selectbox("End", column_options, index=min(3, len(column_options)-1), key=f"batch_end_{selected_run_id}")
                if st.sidebar.button("Apply", key=f"batch_apply_{selected_run_id}"):
                    result_df = subtract_blank_from_time_series(df, blank_method='average', blank_start=blank_start, blank_end=blank_end)
                    selected_run.processed_df = result_df
                    selected_run.blank_config = {'enabled': True, 'applied': True, 'method': 'average', 'start': blank_start, 'end': blank_end}
                    runs[selected_run_id] = process_single_run(selected_run)
    else:
        if st.sidebar.button("Reset", key=f"batch_reset_{selected_run_id}"):
            selected_run.processed_df = None
            selected_run.blank_config = {'enabled': False, 'applied': False}
            runs[selected_run_id] = process_single_run(selected_run)

    return runs


def preprocess_time_series_data(df):
    """Clean time series data"""
    if df.empty:
        return df

    numeric_cols = df.dtypes[df.dtypes.apply(lambda x: pd.api.types.is_numeric_dtype(x))].index
    numeric_df = df[numeric_cols]

    if numeric_df.empty:
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        numeric_df = df.select_dtypes(include=['number'])

    try:
        numeric_df.index = pd.to_numeric(numeric_df.index, errors='coerce')
    except:
        pass

    numeric_df = numeric_df.dropna(how='all')
    numeric_df = numeric_df.dropna(axis=1, how='all')

    return numeric_df


def calculate_integrals(df):
    """Calculate integrals"""
    try:
        numeric_df = df.select_dtypes(include=['number'])
        if numeric_df.empty:
            return pd.Series(dtype=float)

        if not pd.api.types.is_numeric_dtype(numeric_df.index):
            numeric_df.index = pd.to_numeric(numeric_df.index, errors='coerce')
        numeric_df = numeric_df.sort_index().dropna(how='all')

        return numeric_df.apply(lambda col: simpson(col, x=numeric_df.index), axis=0)
    except:
        return pd.Series(dtype=float)


def calculate_avg_emission_wavelength(df):
    """Calculate AEW"""
    try:
        numeric_df = df.select_dtypes(include=['number'])
        if numeric_df.empty:
            return []

        if not pd.api.types.is_numeric_dtype(numeric_df.index):
            numeric_df.index = pd.to_numeric(numeric_df.index, errors='coerce')
        numeric_df = numeric_df.sort_index().dropna(how='all')

        avg_emission_wavelength = []
        for col in numeric_df.columns:
            if (numeric_df[col] <= 0).all():
                avg_emission_wavelength.append(np.nan)
                continue
            weighted_sum = np.sum(numeric_df.index * numeric_df[col])
            total_intensity = np.sum(numeric_df[col])
            avg_emission_wavelength.append(weighted_sum / total_intensity if total_intensity > 0 else np.nan)

        return avg_emission_wavelength
    except:
        return []


def calculate_max_emission_wavelength(df):
    """Find max wavelength"""
    try:
        numeric_df = df.select_dtypes(include=['number'])
        if numeric_df.empty:
            return []

        if not pd.api.types.is_numeric_dtype(numeric_df.index):
            numeric_df.index = pd.to_numeric(numeric_df.index, errors='coerce')
        numeric_df = numeric_df.sort_index().dropna(how='all')

        return [numeric_df.index[np.argmax(numeric_df[col])] for col in numeric_df.columns]
    except:
        return []


def calculate_spectral_width(df, avg_emission_wavelength):
    """Calculate spectral width (weighted standard deviation) for each spectrum"""
    try:
        numeric_df = df.select_dtypes(include=['number'])
        if numeric_df.empty:
            return []

        if not pd.api.types.is_numeric_dtype(numeric_df.index):
            numeric_df.index = pd.to_numeric(numeric_df.index, errors='coerce')
        numeric_df = numeric_df.sort_index().dropna(how='all')

        wavelengths = numeric_df.index.values
        widths = []

        for i, col in enumerate(numeric_df.columns):
            spectrum = numeric_df[col].values
            aew = avg_emission_wavelength[i] if i < len(avg_emission_wavelength) else np.nan

            if np.isnan(aew) or np.sum(spectrum) <= 0:
                widths.append(np.nan)
                continue

            # Weighted standard deviation: sqrt(sum(I * (wl - aew)^2) / sum(I))
            weighted_var = np.sum(spectrum * (wavelengths - aew) ** 2) / np.sum(spectrum)
            widths.append(np.sqrt(weighted_var))

        return widths
    except:
        return []


def augment_dataframe(df, avg_emission_wavelength, integrals, max_emission_wavelength, spectral_width):
    """Combine metrics into dataframe"""
    try:
        df_transposed = df.transpose()
        df_transposed_aew_integral = df_transposed.copy()
        df_transposed_aew_integral["Average emission wavelength [nm]"] = avg_emission_wavelength
        df_transposed_aew_integral["Integral"] = integrals
        df_transposed_aew_integral["Max emission wavelength [nm]"] = max_emission_wavelength
        df_transposed_aew_integral["Spectral width [nm]"] = spectral_width
        df_transposed_aew_integral.reset_index(inplace=True)
        df_transposed_aew_integral.rename(columns={df_transposed_aew_integral.columns[0]: "Process Time [min]"}, inplace=True)

        try:
            df_transposed_aew_integral["Process Time [min]"] = pd.to_numeric(df_transposed_aew_integral["Process Time [min]"], errors='coerce')
        except:
            df_transposed_aew_integral["Process Time [min]"] = range(len(df_transposed_aew_integral))

        df_transposed_aew_integral["Process Time [h]"] = round(df_transposed_aew_integral["Process Time [min]"] / 60, 3)

        return df_transposed, df_transposed_aew_integral
    except:
        return pd.DataFrame(), pd.DataFrame()


def closest_times(df, interval):
    """Find closest times for interval"""
    try:
        available_times = df['Process Time [h]'].values
        interval_times = np.arange(0, available_times.max() + interval, interval)
        closest_indices = []
        for t in interval_times:
            idx = np.abs(available_times - t).argmin()
            if idx not in closest_indices:
                closest_indices.append(idx)
        return df.iloc[closest_indices]
    except:
        return df


# ============== KINETIC FITTING FUNCTIONS ==============

def exponential_decay(t, A, k, y_end):
    """y = A * exp(-k * t) + y_end"""
    return A * np.exp(-k * t) + y_end


def exponential_rise(t, A, k, y_start):
    """y = A * (1 - exp(-k * t)) + y_start"""
    return A * (1 - np.exp(-k * t)) + y_start


def fit_kinetic_data(time_data, y_data, model='decay'):
    """Fit exponential model to kinetic data with validation"""
    try:
        mask = ~(np.isnan(time_data) | np.isnan(y_data))
        t_clean = time_data[mask]
        y_clean = y_data[mask]

        if len(t_clean) < 4:
            return {'success': False, 'error': 'Not enough data points'}

        y_min, y_max = np.min(y_clean), np.max(y_clean)
        y_range = y_max - y_min
        t_max = np.max(t_clean)

        # Check if there's meaningful kinetic change (amplitude > 0.5 nm for AEW)
        if y_range < 0.5:
            return {'success': False, 'error': f'No significant kinetic change (Δy = {y_range:.2f} < 0.5 nm)'}

        if model == 'decay':
            y_end_est = y_clean[-5:].mean() if len(y_clean) > 5 else y_clean[-1]
            A_est = abs(y_clean[0] - y_end_est)
            k_est = 1.0 / (t_max / 3) if t_max > 0 else 1.0
            bounds = ([0, 1e-6, y_min - 50], [y_max * 2, 100, y_max + 50])
            p0 = [A_est, k_est, y_end_est]
            fit_func = exponential_decay
        else:
            y_start_est = y_clean[0]
            A_est = abs(y_clean[-5:].mean() - y_start_est) if len(y_clean) > 5 else abs(y_clean[-1] - y_start_est)
            k_est = 1.0 / (t_max / 3) if t_max > 0 else 1.0
            bounds = ([-y_max * 2, 1e-6, y_min - 50], [y_max * 2, 100, y_max + 50])
            p0 = [A_est, k_est, y_start_est]
            fit_func = exponential_rise

        popt, pcov = curve_fit(fit_func, t_clean, y_clean, p0=p0, bounds=bounds, maxfev=10000)

        n = len(t_clean)
        p = len(popt)
        dof = max(1, n - p)
        perr = np.sqrt(np.diag(pcov))
        t_val = t.ppf(0.975, dof)
        ci_lower = popt - t_val * perr
        ci_upper = popt + t_val * perr

        y_pred = fit_func(t_clean, *popt)
        ss_res = np.sum((y_clean - y_pred) ** 2)
        ss_tot = np.sum((y_clean - np.mean(y_clean)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        k_fit = popt[1]
        t_half = np.log(2) / k_fit if k_fit > 0 else np.inf

        # Check fit quality
        if r_squared < 0.5:
            return {'success': False, 'error': f'Poor fit quality (R² = {r_squared:.3f} < 0.5)'}

        # Check for unreasonably fast kinetics (t_1/2 < 1 minute is likely spurious)
        if t_half < 1/60:  # less than 1 minute
            return {'success': False, 'error': f'Unreasonably fast kinetics (t_1/2 = {t_half*60:.1f} s < 60 s)'}

        offset_name = 'y_end' if model == 'decay' else 'y_start'

        return {
            'success': True,
            'model': model,
            'parameters': {
                'A': {'value': popt[0], 'ci_lower': ci_lower[0], 'ci_upper': ci_upper[0]},
                'k': {'value': popt[1], 'ci_lower': ci_lower[1], 'ci_upper': ci_upper[1]},
                offset_name: {'value': popt[2], 'ci_lower': ci_lower[2], 'ci_upper': ci_upper[2]},
            },
            'offset_name': offset_name,
            't_half': {'value': t_half},
            'r_squared': r_squared,
            'fitted_curve': {'t': t_clean, 'y_pred': y_pred}
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def plot_kinetic_fit(df, fit_result):
    """Plot data and fitted curve"""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['Process Time [h]'],
        y=df['Average emission wavelength [nm]'],
        mode='markers',
        name='Data',
        marker=dict(size=8, color='#1f77b4')
    ))

    if fit_result['success']:
        t_data = df['Process Time [h]'].dropna().values
        t_max = np.nanmax(t_data)
        t_smooth = np.linspace(0, t_max * 1.1, 200)

        model = fit_result['model']
        A = fit_result['parameters']['A']['value']
        k = fit_result['parameters']['k']['value']
        offset_name = fit_result['offset_name']
        offset = fit_result['parameters'][offset_name]['value']

        if model == 'decay':
            y_smooth = exponential_decay(t_smooth, A, k, offset)
            fit_label = 'Exponential Decay'
        else:
            y_smooth = exponential_rise(t_smooth, A, k, offset)
            fit_label = 'Exponential Rise'

        fig.add_trace(go.Scatter(
            x=t_smooth,
            y=y_smooth,
            mode='lines',
            name=fit_label,
            line=dict(color='#d62728', width=2)
        ))

        annotation_text = (
            f"k<sub>obs</sub> = {fit_result['parameters']['k']['value']:.4f} h<sup>-1</sup><br>"
            f"t<sub>1/2</sub> = {fit_result['t_half']['value']:.2f} h<br>"
            f"R² = {fit_result['r_squared']:.4f}"
        )

        fig.add_annotation(x=0.98, y=0.98, xref='paper', yref='paper', text=annotation_text,
                          showarrow=False, bgcolor='rgba(255,255,255,0.9)', bordercolor='gray',
                          borderwidth=1, font=dict(size=12), align='left')

    fig.update_layout(autosize=False, width=width, height=height, template=dark_template,
                     xaxis_title="Process Time [h]", yaxis_title="Average Emission Wavelength [nm]",
                     legend=dict(x=0.02, y=0.98))

    return fig


def plot_batch_kinetics_comparison(runs, fit_results):
    """Bar chart comparing rate constants"""
    fig = go.Figure()

    names = []
    k_values = []
    k_errors = []

    for run_id, fit in fit_results.items():
        if fit['success']:
            run = runs[run_id]
            names.append(run.file_name)
            k_val = fit['parameters']['k']['value']
            k_values.append(k_val)
            k_errors.append(fit['parameters']['k']['ci_upper'] - fit['parameters']['k']['ci_lower'])

    if names:
        colors = generate_colors(len(names))
        fig.add_trace(go.Bar(x=names, y=k_values, error_y=dict(type='data', array=k_errors), marker_color=colors))

    fig.update_layout(autosize=False, width=width, height=height, template=dark_template,
                     xaxis_title="Run", yaxis_title="k<sub>obs</sub> (h<sup>-1</sup>)", showlegend=False)

    return fig


def create_kinetics_summary_table(runs, fit_results):
    """Summary table of kinetic parameters"""
    data = []
    for run_id, fit in fit_results.items():
        run = runs[run_id]
        if fit['success']:
            data.append({
                'Run': run.file_name,
                'Model': fit['model'],
                'k_obs (h⁻¹)': fit['parameters']['k']['value'],
                'k CI Lower': fit['parameters']['k']['ci_lower'],
                'k CI Upper': fit['parameters']['k']['ci_upper'],
                't_1/2 (h)': fit['t_half']['value'],
                'R²': fit['r_squared']
            })
        else:
            data.append({'Run': run.file_name, 'Model': 'Failed'})

    return pd.DataFrame(data)


# ============== BATCH PROCESSING FUNCTIONS ==============

def generate_colors(n):
    """Generate n distinct colors using emission-inspired palette"""
    if n <= len(EMISSION_PALETTE):
        return EMISSION_PALETTE[:n]
    # If more colors needed, extend the palette
    colors = list(EMISSION_PALETTE)
    for i in range(n - len(EMISSION_PALETTE)):
        hue = (i + len(EMISSION_PALETTE)) / n
        rgb = colorsys.hsv_to_rgb(hue, 0.7, 0.9)
        colors.append(f'rgb({int(rgb[0]*255)}, {int(rgb[1]*255)}, {int(rgb[2]*255)})')
    return colors


def process_single_run(run):
    """Process a single run"""
    try:
        df = run.processed_df if run.processed_df is not None else run.raw_df

        integrals = calculate_integrals(df)
        avg_emission_wavelength = calculate_avg_emission_wavelength(df)
        max_emission_wavelength = calculate_max_emission_wavelength(df)
        spectral_width = calculate_spectral_width(df, avg_emission_wavelength)
        df_transposed, df_augmented = augment_dataframe(df, avg_emission_wavelength, integrals, max_emission_wavelength, spectral_width)

        run.metrics = {
            'aew': avg_emission_wavelength,
            'max_wl': max_emission_wavelength,
            'integral': integrals,
            'spectral_width': spectral_width,
            'augmented_df': df_augmented,
            'df_transposed': df_transposed
        }
        run.status = 'complete'
    except Exception as e:
        run.status = 'error'

    return run


def plot_data(df, y_column):
    """Scatter plot"""
    fig = px.scatter(df, x="Process Time [h]", y=y_column, template=dark_template)
    fig.update_layout(autosize=False, width=width, height=height)
    return fig


def plot_intensity(df, interval=None):
    """Plot intensity spectra"""
    try:
        if interval is not None:
            df = closest_times(df, interval)
            df = df.reset_index(drop=True)

        df_plot = df.T
        df_plot.columns = df_plot.iloc[-1]
        df_plot = df_plot[:-4]

        fig = go.Figure()
        for i in range(df_plot.shape[1]):
            fig.add_trace(go.Scatter(
                x=df_plot.index,
                y=df_plot[df_plot.columns[i]],
                name=str(df_plot.columns[i]),
                customdata=np.tile(df_plot.columns[i], len(df_plot.index)),
                hovertemplate='<b>Time:</b> %{customdata}<br><b>WL:</b> %{x}<br><b>Int:</b> %{y}<extra></extra>',
            ))

        fig.update_layout(width=width, height=height, template=dark_template,
                         xaxis_title="Wavelength [nm]", yaxis_title="Intensity", legend_title="Process Time [h]")
        return fig
    except:
        return go.Figure()


def plot_contour(df):
    """Contour plot"""
    try:
        numeric_df = df.select_dtypes(include=['number'])
        if numeric_df.empty:
            return go.Figure()

        if not pd.api.types.is_numeric_dtype(numeric_df.index):
            numeric_df.index = pd.to_numeric(numeric_df.index, errors='coerce')

        numeric_df = numeric_df.sort_index().dropna(how='all')

        Z = numeric_df.to_numpy()
        X = np.array(numeric_df.index, dtype=float)
        Y = np.array(numeric_df.columns, dtype=float)

        fig = go.Figure(data=go.Contour(z=Z, x=X, y=Y, colorscale='Viridis',
                                        hovertemplate='WL: %{x}<br>Time: %{y}<br>Int: %{z}<extra></extra>',
                                        colorbar=dict(title="Intensity")))

        fig.update_layout(autosize=False, width=width, height=height, template=dark_template,
                         xaxis_title='Wavelength [nm]', yaxis_title='Time')
        return fig
    except:
        return go.Figure()


def plot_batch_comparison(runs, metric):
    """Overlay comparison plot"""
    fig = go.Figure()
    colors = generate_colors(len(runs))

    for idx, (run_id, run) in enumerate(runs.items()):
        if run.status != 'complete' or 'augmented_df' not in run.metrics:
            continue
        df = run.metrics['augmented_df']
        if metric not in df.columns:
            continue

        fig.add_trace(go.Scatter(
            x=df["Process Time [h]"],
            y=df[metric],
            mode='lines+markers',
            name=run.file_name,
            line=dict(color=colors[idx]),
            marker=dict(color=colors[idx])
        ))

    fig.update_layout(autosize=False, width=width, height=height, template=dark_template,
                     xaxis_title="Process Time [h]", yaxis_title=metric, legend_title="Run")
    return fig


def create_batch_metrics_summary(runs):
    """Summary table for batch"""
    all_data = []
    for run_id, run in runs.items():
        if run.status != 'complete' or 'augmented_df' not in run.metrics:
            continue
        df = run.metrics['augmented_df']
        for _, row in df.iterrows():
            all_data.append({
                'Run': run.file_name,
                'Process Time [h]': row.get('Process Time [h]', np.nan),
                'AEW [nm]': row.get('Average emission wavelength [nm]', np.nan),
                'Max WL [nm]': row.get('Max emission wavelength [nm]', np.nan),
                'Spectral Width [nm]': row.get('Spectral width [nm]', np.nan),
                'Integral': row.get('Integral', np.nan)
            })
    return pd.DataFrame(all_data) if all_data else pd.DataFrame()


def save_batch_to_excel(runs):
    """Save batch to Excel"""
    try:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            summary_df = create_batch_metrics_summary(runs)
            if not summary_df.empty:
                summary_df.to_excel(writer, sheet_name='Summary', index=False)

            for run_id, run in runs.items():
                if run.status != 'complete' or 'augmented_df' not in run.metrics:
                    continue
                sheet_name = run.file_name[:28] + "..." if len(run.file_name) > 31 else run.file_name
                sheet_name = sheet_name.replace('[', '(').replace(']', ')').replace(':', '-')
                run.metrics['augmented_df'].to_excel(writer, sheet_name=sheet_name, index=False)

        output.seek(0)
        return output.getvalue()
    except:
        return b''


def export_tidy_csv_with_provenance(runs, analysis_params: dict = None):
    """
    Export tidy CSV with all runs and provenance metadata.

    Returns CSV string with:
    - Header comments containing provenance (app version, parameters, timestamp)
    - Tidy data with columns: run, process_time_h, aew_nm, integral, max_wavelength_nm
    """
    import datetime

    # Build tidy dataframe
    all_rows = []
    for run_id, run in runs.items():
        if run.status != 'complete' or 'augmented_df' not in run.metrics:
            continue
        df = run.metrics['augmented_df']
        for _, row in df.iterrows():
            all_rows.append({
                'run': run.file_name,
                'process_time_h': row.get('Process Time [h]', np.nan),
                'aew_nm': row.get('Average emission wavelength [nm]', np.nan),
                'integral': row.get('Integral', np.nan),
                'max_wavelength_nm': row.get('Max emission wavelength [nm]', np.nan),
                'spectral_width_nm': row.get('Spectral width [nm]', np.nan)
            })

    if not all_rows:
        return ""

    tidy_df = pd.DataFrame(all_rows)

    # Build provenance header
    provenance_lines = [
        "# FluoroSense Time Series Export",
        f"# Generated: {datetime.datetime.now().isoformat()}",
        f"# Total runs: {len(runs)}",
        f"# Complete runs: {sum(1 for r in runs.values() if r.status == 'complete')}",
    ]

    if analysis_params:
        provenance_lines.append("# Analysis Parameters:")
        for key, value in analysis_params.items():
            provenance_lines.append(f"#   {key}: {value}")

    # Add blank subtraction info per run
    provenance_lines.append("# Blank Subtraction Config:")
    for run_id, run in runs.items():
        if run.blank_config:
            provenance_lines.append(f"#   {run.file_name}: {run.blank_config}")

    provenance_header = "\n".join(provenance_lines) + "\n\n"

    return provenance_header + tidy_df.to_csv(index=False)


def save_to_excel(header, df):
    """Save single file to Excel"""
    try:
        header_df = pd.DataFrame.from_dict(header, orient='index', columns=['Value'])
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Data', index=False)
            header_df.to_excel(writer, sheet_name='Info')
        output.seek(0)
        return output.getvalue()
    except:
        return b''


def df_to_txt(df, y_column):
    """Convert to txt"""
    try:
        df_subset = df[["Process Time [h]", y_column]]
        str_io = StringIO()
        df_subset.to_csv(str_io, sep='\t', index=False)
        return str_io.getvalue()
    except:
        return ""


# ============== PHASE PORTRAIT FUNCTIONS ==============

def plot_phase_portrait(df):
    """Create spectral phase portrait (Width vs AEW) for a single run"""
    try:
        if 'Average emission wavelength [nm]' not in df.columns or 'Spectral width [nm]' not in df.columns:
            return go.Figure()

        aew = df['Average emission wavelength [nm]'].values
        width = df['Spectral width [nm]'].values
        time = df['Process Time [h]'].values

        # Remove NaN values
        mask = ~(np.isnan(aew) | np.isnan(width) | np.isnan(time))
        aew = aew[mask]
        width = width[mask]
        time = time[mask]

        if len(aew) == 0:
            return go.Figure()

        fig = go.Figure()

        # Line connecting points
        fig.add_trace(go.Scatter(
            x=aew, y=width,
            mode='lines',
            line=dict(color='rgba(0,0,0,0.2)', width=1),
            showlegend=False,
            hoverinfo='skip'
        ))

        # Scatter points colored by time
        fig.add_trace(go.Scatter(
            x=aew, y=width,
            mode='markers',
            marker=dict(
                size=8,
                color=time,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title='Time [h]')
            ),
            name='Trajectory',
            customdata=time,
            hovertemplate='<b>AEW:</b> %{x:.2f} nm<br><b>Width:</b> %{y:.2f} nm<br><b>Time:</b> %{customdata:.2f} h<extra></extra>'
        ))

        # Start marker (green)
        fig.add_trace(go.Scatter(
            x=[aew[0]], y=[width[0]],
            mode='markers',
            marker=dict(size=12, color='green', symbol='circle'),
            name='Start',
            hovertemplate='<b>START</b><br>AEW: %{x:.2f} nm<br>Width: %{y:.2f} nm<extra></extra>'
        ))

        # End marker (red)
        fig.add_trace(go.Scatter(
            x=[aew[-1]], y=[width[-1]],
            mode='markers',
            marker=dict(size=12, color='red', symbol='circle'),
            name='End',
            hovertemplate='<b>END</b><br>AEW: %{x:.2f} nm<br>Width: %{y:.2f} nm<extra></extra>'
        ))

        # Invert x-axis so higher AEW is on the left (folding goes left-to-right)
        aew_range = max(aew) - min(aew)
        fig.update_xaxes(autorange="reversed")

        fig.update_layout(
            autosize=False, width=width, height=height, template=dark_template,
            xaxis_title="Average Emission Wavelength [nm]",
            yaxis_title="Spectral Width [nm]",
            legend=dict(x=0.02, y=0.98)
        )

        return fig
    except Exception as e:
        return go.Figure()


def plot_batch_phase_portraits(runs, cols=3):
    """Create grid of phase portraits for batch mode using Plotly subplots"""
    from plotly.subplots import make_subplots

    complete_runs = [(run_id, run) for run_id, run in runs.items()
                     if run.status == 'complete' and 'augmented_df' in run.metrics]

    if not complete_runs:
        return go.Figure()

    n_runs = len(complete_runs)
    rows = (n_runs + cols - 1) // cols

    fig = make_subplots(
        rows=rows, cols=cols,
        subplot_titles=[run.file_name for _, run in complete_runs],
        horizontal_spacing=0.08,
        vertical_spacing=0.1
    )

    for idx, (run_id, run) in enumerate(complete_runs):
        df = run.metrics['augmented_df']
        row = idx // cols + 1
        col = idx % cols + 1

        if 'Average emission wavelength [nm]' not in df.columns or 'Spectral width [nm]' not in df.columns:
            continue

        aew = df['Average emission wavelength [nm]'].values
        spectral_width = df['Spectral width [nm]'].values
        time_vals = df['Process Time [h]'].values

        mask = ~(np.isnan(aew) | np.isnan(spectral_width) | np.isnan(time_vals))
        aew, spectral_width, time_vals = aew[mask], spectral_width[mask], time_vals[mask]

        if len(aew) == 0:
            continue

        # Line
        fig.add_trace(go.Scatter(
            x=aew, y=spectral_width,
            mode='lines',
            line=dict(color='rgba(0,0,0,0.3)', width=1),
            showlegend=False
        ), row=row, col=col)

        # Points colored by time
        fig.add_trace(go.Scatter(
            x=aew, y=spectral_width,
            mode='markers',
            marker=dict(size=6, color=time_vals, colorscale='Viridis'),
            showlegend=False
        ), row=row, col=col)

        # Start marker
        fig.add_trace(go.Scatter(
            x=[aew[0]], y=[spectral_width[0]],
            mode='markers',
            marker=dict(size=8, color='green'),
            showlegend=False
        ), row=row, col=col)

        # End marker
        fig.add_trace(go.Scatter(
            x=[aew[-1]], y=[spectral_width[-1]],
            mode='markers',
            marker=dict(size=8, color='red'),
            showlegend=False
        ), row=row, col=col)

        # Invert x-axis for each subplot
        fig.update_xaxes(autorange="reversed", row=row, col=col)
        fig.update_xaxes(title_text="AEW [nm]", row=row, col=col, title_font=dict(size=10))
        fig.update_yaxes(title_text="Width [nm]", row=row, col=col, title_font=dict(size=10))

    fig.update_layout(
        autosize=False,
        width=width,
        height=max(height, 300 * rows),
        template=dark_template
    )

    return fig


def plot_batch_aew_grid(runs, cols=3):
    """Create grid of AEW vs Time plots for batch mode"""
    from plotly.subplots import make_subplots

    complete_runs = [(run_id, run) for run_id, run in runs.items()
                     if run.status == 'complete' and 'augmented_df' in run.metrics]

    if not complete_runs:
        return go.Figure()

    n_runs = len(complete_runs)
    rows = (n_runs + cols - 1) // cols

    fig = make_subplots(
        rows=rows, cols=cols,
        subplot_titles=[run.file_name for _, run in complete_runs],
        horizontal_spacing=0.08,
        vertical_spacing=0.1
    )

    for idx, (run_id, run) in enumerate(complete_runs):
        df = run.metrics['augmented_df']
        row = idx // cols + 1
        col = idx % cols + 1

        if 'Average emission wavelength [nm]' not in df.columns or 'Process Time [h]' not in df.columns:
            continue

        aew = df['Average emission wavelength [nm]'].values
        time_vals = df['Process Time [h]'].values

        mask = ~(np.isnan(aew) | np.isnan(time_vals))
        aew, time_vals = aew[mask], time_vals[mask]

        if len(aew) == 0:
            continue

        # AEW line
        fig.add_trace(go.Scatter(
            x=time_vals, y=aew,
            mode='lines',
            line=dict(color='#00d4ff', width=1.5),
            showlegend=False
        ), row=row, col=col)

        fig.update_xaxes(title_text="Time [h]", row=row, col=col, title_font=dict(size=10))
        fig.update_yaxes(title_text="AEW [nm]", row=row, col=col, title_font=dict(size=10))

    fig.update_layout(
        autosize=False,
        width=width,
        height=max(height, 300 * rows),
        template=dark_template
    )

    return fig


def plot_kinetics_overlay(runs, batch_fit_results, batch_selected_model):
    """Create overlay plot of AEW data with kinetic fits for all runs"""
    fig = go.Figure()
    colors = generate_colors(len(runs))

    for idx, (run_id, run) in enumerate(runs.items()):
        if run.status != 'complete' or 'augmented_df' not in run.metrics:
            continue
        df = run.metrics['augmented_df']

        # Plot AEW data points
        fig.add_trace(go.Scatter(
            x=df["Process Time [h]"],
            y=df["Average emission wavelength [nm]"],
            mode='markers',
            name=run.file_name,
            marker=dict(color=colors[idx], size=8),
            showlegend=True
        ))

        # Plot fitted curve if available
        if run_id in batch_fit_results and batch_fit_results[run_id]['success']:
            fit = batch_fit_results[run_id]
            t_data = df['Process Time [h]'].dropna().values
            t_max = np.nanmax(t_data)
            t_smooth = np.linspace(0, t_max * 1.1, 200)

            A = fit['parameters']['A']['value']
            k = fit['parameters']['k']['value']
            offset_name = fit['offset_name']
            offset = fit['parameters'][offset_name]['value']

            if fit['model'] == 'decay':
                y_smooth = exponential_decay(t_smooth, A, k, offset)
            else:
                y_smooth = exponential_rise(t_smooth, A, k, offset)

            fig.add_trace(go.Scatter(
                x=t_smooth,
                y=y_smooth,
                mode='lines',
                name=f"{run.file_name} (fit)",
                line=dict(color=colors[idx], width=2, dash='solid'),
                showlegend=False
            ))

    fig.update_layout(
        autosize=False, width=width, height=height, template=dark_template,
        xaxis_title="Process Time [h]", yaxis_title="Average Emission Wavelength [nm]",
        legend_title="Run"
    )
    return fig


def plot_kinetics_grid(runs, batch_fit_results, batch_selected_model, cols=3):
    """Create grid plot of AEW data with kinetic fits for each run"""
    from plotly.subplots import make_subplots

    complete_runs = [(run_id, run) for run_id, run in runs.items()
                     if run.status == 'complete' and 'augmented_df' in run.metrics]

    if not complete_runs:
        return go.Figure()

    n_runs = len(complete_runs)
    rows = (n_runs + cols - 1) // cols
    colors = generate_colors(n_runs)

    fig = make_subplots(
        rows=rows, cols=cols,
        subplot_titles=[run.file_name for _, run in complete_runs],
        horizontal_spacing=0.08,
        vertical_spacing=0.12
    )

    for idx, (run_id, run) in enumerate(complete_runs):
        df = run.metrics['augmented_df']
        row = idx // cols + 1
        col = idx % cols + 1

        if 'Average emission wavelength [nm]' not in df.columns or 'Process Time [h]' not in df.columns:
            continue

        time_vals = df['Process Time [h]'].values
        aew = df['Average emission wavelength [nm]'].values

        mask = ~(np.isnan(aew) | np.isnan(time_vals))
        aew, time_vals = aew[mask], time_vals[mask]

        if len(aew) == 0:
            continue

        # AEW data points
        fig.add_trace(go.Scatter(
            x=time_vals, y=aew,
            mode='markers',
            marker=dict(color=colors[idx], size=6),
            showlegend=False
        ), row=row, col=col)

        # Fitted curve if available
        if run_id in batch_fit_results and batch_fit_results[run_id]['success']:
            fit = batch_fit_results[run_id]
            t_max = np.nanmax(time_vals)
            t_smooth = np.linspace(0, t_max * 1.1, 200)

            A = fit['parameters']['A']['value']
            k = fit['parameters']['k']['value']
            offset_name = fit['offset_name']
            offset = fit['parameters'][offset_name]['value']

            if fit['model'] == 'decay':
                y_smooth = exponential_decay(t_smooth, A, k, offset)
            else:
                y_smooth = exponential_rise(t_smooth, A, k, offset)

            fig.add_trace(go.Scatter(
                x=t_smooth, y=y_smooth,
                mode='lines',
                line=dict(color=colors[idx], width=2),
                showlegend=False
            ), row=row, col=col)

        fig.update_xaxes(title_text="Time [h]", row=row, col=col, title_font=dict(size=10))
        fig.update_yaxes(title_text="AEW [nm]", row=row, col=col, title_font=dict(size=10))

    fig.update_layout(
        autosize=False,
        width=width,
        height=max(height, 280 * rows),
        template=dark_template
    )
    return fig


# ============== SESSION STATE ==============

if 'blank_subtraction_applied' not in st.session_state:
    st.session_state['blank_subtraction_applied'] = False
if 'batch_runs' not in st.session_state:
    st.session_state['batch_runs'] = {}
if 'processing_mode' not in st.session_state:
    st.session_state['processing_mode'] = "Single File"
if 'batch_fit_cache' not in st.session_state:
    st.session_state['batch_fit_cache'] = {}
if 'batch_fit_cache_key' not in st.session_state:
    st.session_state['batch_fit_cache_key'] = None


# ============== MAIN APPLICATION ==============

processing_mode = st.sidebar.radio("Processing Mode", ["Single File", "Batch Processing"], index=0)
st.session_state['processing_mode'] = processing_mode

if processing_mode == "Single File":
    with st.expander("Upload file here"):
        uploaded_file = st.sidebar.file_uploader("Choose CSV file", key="single")

    if uploaded_file:
        header, df, extended_info = upload_jasco_rawdata(uploaded_file)
        df = preprocess_time_series_data(df)
        df = blank_subtraction_ui(df)

        integrals = calculate_integrals(df)
        avg_emission_wavelength = calculate_avg_emission_wavelength(df)
        max_emission_wavelength = calculate_max_emission_wavelength(df)
        spectral_width = calculate_spectral_width(df, avg_emission_wavelength)
        df_transposed, df_augmented = augment_dataframe(df, avg_emission_wavelength, integrals, max_emission_wavelength, spectral_width)

        file_suffix = "_blank_subtracted" if st.session_state.get('blank_subtraction_applied', False) else ""

        excel_data = save_to_excel(header, df_augmented)
        st.sidebar.download_button("Download Excel", data=excel_data,
                                   file_name=header.get("TITLE", "data") + "_processed" + file_suffix + ".xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        if header:
            st.sidebar.write("---")
            for key, value in header.items():
                st.sidebar.text(f"{key}: {value}")

        if st.session_state.get('blank_subtraction_applied', False):
            st.info("Blank subtraction applied.")

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
            ["Experiment all", "Average Emission Wavelength", "Max Emission Wavelength", "Integral of Intensities", "Phase Portrait", "Contour"])

        with tab1:
            interval = st.select_slider('Select time interval of plotted graphs',
                                        options=[None, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2], value=0.25)
            st.plotly_chart(plot_intensity(df_augmented, interval=interval), width='stretch', config=config)

        with tab2:
            st.header("Average Emission Wavelength [nm]")

            # Kinetics checkbox
            analyze_kinetics = st.checkbox("Analyze Kinetics", value=False, key="single_kinetics_checkbox")

            if analyze_kinetics:
                kinetic_model = st.radio("Model", ["Decay", "Rise"], horizontal=True,
                                        help="Decay: y = A·exp(-k·t) + y∞ (signal decreases)\nRise: y = A·(1-exp(-k·t)) + y₀ (signal increases)")
                st.markdown(f"**Equation:** {'y = A · exp(-k · t) + y∞' if kinetic_model == 'Decay' else 'y = A · (1 - exp(-k · t)) + y₀'}")

                selected_model = 'decay' if kinetic_model == 'Decay' else 'rise'
                time_data = df_augmented['Process Time [h]'].values
                aew_data = df_augmented['Average emission wavelength [nm]'].values
                fit_result = fit_kinetic_data(time_data, aew_data, model=selected_model)

                if fit_result['success']:
                    # Show AEW plot with fit overlay
                    st.plotly_chart(plot_kinetic_fit(df_augmented, fit_result), width='stretch', config=config)

                    # Show kinetic parameters
                    st.subheader("Kinetic Parameters")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("k_obs (h⁻¹)", f"{fit_result['parameters']['k']['value']:.4f}",
                                 f"95% CI: [{fit_result['parameters']['k']['ci_lower']:.4f}, {fit_result['parameters']['k']['ci_upper']:.4f}]")
                    with col2:
                        st.metric("t_1/2 (h)", f"{fit_result['t_half']['value']:.2f}")
                    with col3:
                        st.metric("R²", f"{fit_result['r_squared']:.4f}")

                    # Export fit data
                    fit_csv = pd.DataFrame({
                        'Process Time [h]': time_data,
                        'AEW Data [nm]': aew_data,
                        'AEW Fit [nm]': fit_result['fitted_curve']['y_pred']
                    }).to_csv(index=False).encode('utf-8')
                    st.download_button("Download Fit Data as CSV", data=fit_csv,
                                      file_name=header.get("TITLE", "kinetic_fit") + "_kinetic_fit.csv", mime='text/csv')
                else:
                    st.error(f"Kinetic fitting failed: {fit_result.get('error', 'Unknown')}")
                    st.plotly_chart(plot_data(df_augmented, "Average emission wavelength [nm]"), width='stretch', config=config)
            else:
                # Just show regular AEW plot
                st.plotly_chart(plot_data(df_augmented, "Average emission wavelength [nm]"), width='stretch', config=config)

        with tab3:
            st.header("Max Emission Wavelength [nm]")
            st.plotly_chart(plot_data(df_augmented, "Max emission wavelength [nm]"), width='stretch', config=config)

        with tab4:
            st.header("Integral of the intensity")
            st.plotly_chart(plot_data(df_augmented, "Integral"), width='stretch', config=config)

        with tab5:
            st.header("Spectral Phase Portrait")
            st.markdown("Width vs AEW trajectory showing protein folding dynamics. Green = start, Red = end.")
            st.plotly_chart(plot_phase_portrait(df_augmented), width='stretch', config=config)

        with tab6:
            st.header("Contour plot")
            st.plotly_chart(plot_contour(df_transposed), width='stretch', config=config)

else:
    # Batch mode
    with st.expander("Upload files"):
        uploaded_files = st.sidebar.file_uploader("Choose CSV files", accept_multiple_files=True, key="batch")

    if uploaded_files:
        current_file_names = {f.name for f in uploaded_files}
        existing_file_names = {run.file_name for run in st.session_state['batch_runs'].values()}

        if current_file_names != existing_file_names:
            st.session_state['batch_runs'] = {}
            # Clear kinetics cache when files change
            st.session_state['batch_fit_cache'] = {}
            st.session_state['batch_fit_cache_key'] = None
            progress_bar = st.progress(0)
            status_text = st.empty()

            for idx, uploaded_file in enumerate(uploaded_files):
                try:
                    status_text.text(f"Processing {uploaded_file.name}...")
                    # Compute content hash for caching
                    file_content = uploaded_file.read()
                    content_hash = compute_content_hash(file_content)
                    uploaded_file.seek(0)  # Reset file pointer

                    header, df, extended_info = upload_jasco_rawdata(uploaded_file)
                    df = preprocess_time_series_data(df)
                    run_id = f"run_{len(st.session_state['batch_runs'])}"
                    run = TimeSeriesRun(
                        run_id=run_id,
                        file_name=uploaded_file.name,
                        header=header,
                        raw_df=df,
                        content_hash=content_hash,
                        status='pending'
                    )
                    run = process_single_run(run)
                    st.session_state['batch_runs'][run_id] = run
                except Exception as e:
                    st.error(f"Error loading {uploaded_file.name}: {str(e)}")

                progress_bar.progress((idx + 1) / len(uploaded_files))

            progress_bar.empty()
            status_text.empty()

        # Validate wavelength grid consistency
        runs = st.session_state['batch_runs']
        if len(runs) > 1:
            is_valid, warning, mismatched = validate_wavelength_grid(runs)
            if not is_valid:
                st.warning(warning)
                # Option to skip mismatched files
                if mismatched:
                    if st.button("Skip mismatched files", key="skip_mismatched"):
                        for run_id, run in list(runs.items()):
                            if run.file_name in mismatched:
                                del st.session_state['batch_runs'][run_id]
                        st.rerun()

        runs = st.session_state['batch_runs']
        runs = batch_blank_subtraction_ui(runs)
        st.session_state['batch_runs'] = runs

        batch_tabs = st.tabs(["Individual", "AEW Comparison", "Max WL Comparison", "Integral Comparison", "Phase Portraits", "Summary", "Export"], key="batch_main_tabs")

        with batch_tabs[0]:
            st.header("Individual Run")
            run_options = {run.file_name: run_id for run_id, run in runs.items()}
            selected_file = st.selectbox("Select run", list(run_options.keys()))

            if selected_file:
                selected_run = runs[run_options[selected_file]]
                if selected_run.status == 'complete' and 'augmented_df' in selected_run.metrics:
                    interval = st.select_slider('Interval', options=[None, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2], value=0.25)
                    st.plotly_chart(plot_intensity(selected_run.metrics['augmented_df'], interval=interval), width='stretch', config=config)
                    st.plotly_chart(plot_contour(selected_run.metrics['df_transposed']), width='stretch', config=config)

        with batch_tabs[1]:
            st.header("AEW Comparison")

            # View mode toggle - placed at top level so it's always visible
            view_mode = st.radio("View Mode", ["Overlay", "Grid"], horizontal=True, key="aew_view_mode",
                                help="Overlay: all runs on one plot for comparison\nGrid: individual plots per run")

            # Kinetics checkbox for batch mode
            analyze_kinetics_batch = st.checkbox("Analyze Kinetics", value=False, key="batch_kinetics_checkbox")

            # Use a container for the plot to avoid stale rendering
            plot_container = st.container()

            if analyze_kinetics_batch:
                batch_kinetic_model = st.radio("Model", ["Decay", "Rise"], horizontal=True, key="batch_kinetic_model",
                                              help="Decay: y = A·exp(-k·t) + y∞ (signal decreases)\nRise: y = A·(1-exp(-k·t)) + y₀ (signal increases)")
                st.markdown(f"**Equation:** {'y = A · exp(-k · t) + y∞' if batch_kinetic_model == 'Decay' else 'y = A · (1 - exp(-k · t)) + y₀'}")
                batch_selected_model = 'decay' if batch_kinetic_model == 'Decay' else 'rise'

                # Create cache key from run data hashes
                cache_key_data = tuple(
                    (run_id, run.content_hash if hasattr(run, 'content_hash') else str(hash(str(run.metrics.get('augmented_df', '').head() if 'augmented_df' in run.metrics else ''))))
                    for run_id, run in runs.items() if run.status == 'complete'
                )

                # Check if we need to recompute fits
                cache_key = (cache_key_data, batch_selected_model)
                if 'batch_fit_cache' not in st.session_state or st.session_state.get('batch_fit_cache_key') != cache_key:
                    batch_fit_results = {}
                    for run_id, run in runs.items():
                        if run.status == 'complete' and 'augmented_df' in run.metrics:
                            df = run.metrics['augmented_df']
                            batch_fit_results[run_id] = fit_kinetic_data(
                                df['Process Time [h]'].values,
                                df['Average emission wavelength [nm]'].values,
                                model=batch_selected_model
                            )
                    st.session_state['batch_fit_cache'] = batch_fit_results
                    st.session_state['batch_fit_cache_key'] = cache_key
                else:
                    batch_fit_results = st.session_state['batch_fit_cache']

                # Show plot based on view mode (respect the selection)
                with plot_container:
                    if view_mode == "Overlay":
                        st.plotly_chart(plot_kinetics_overlay(runs, batch_fit_results, batch_selected_model), width='stretch', config=config)
                    else:
                        st.plotly_chart(plot_kinetics_grid(runs, batch_fit_results, batch_selected_model), width='stretch', config=config)

                # Show summary table of kinetic parameters
                st.subheader("Kinetic Parameters Summary")
                kinetics_summary = create_kinetics_summary_table(runs, batch_fit_results)
                if not kinetics_summary.empty:
                    st.dataframe(kinetics_summary, width='stretch')
                    st.download_button("Download Kinetics CSV", data=kinetics_summary.to_csv(index=False).encode('utf-8'),
                                      file_name="batch_kinetics.csv", mime='text/csv')

                # Show individual fits in expanders
                st.subheader("Individual Fits")
                for run_id, fit in batch_fit_results.items():
                    run = runs[run_id]
                    with st.expander(run.file_name):
                        if fit['success']:
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("k_obs (h⁻¹)", f"{fit['parameters']['k']['value']:.4f}",
                                         f"95% CI: [{fit['parameters']['k']['ci_lower']:.4f}, {fit['parameters']['k']['ci_upper']:.4f}]")
                            with col2:
                                st.metric("t_1/2 (h)", f"{fit['t_half']['value']:.2f}")
                            with col3:
                                st.metric("R²", f"{fit['r_squared']:.4f}")
                            st.plotly_chart(plot_kinetic_fit(run.metrics['augmented_df'], fit), width='stretch', config=config)
                        else:
                            st.error(f"Failed: {fit.get('error')}")
            else:
                # Show AEW comparison based on view mode
                with plot_container:
                    if view_mode == "Overlay":
                        st.plotly_chart(plot_batch_comparison(runs, "Average emission wavelength [nm]"), width='stretch', config=config)
                    else:
                        st.plotly_chart(plot_batch_aew_grid(runs), width='stretch', config=config)

        with batch_tabs[2]:
            st.header("Max Wavelength Comparison")
            st.plotly_chart(plot_batch_comparison(runs, "Max emission wavelength [nm]"), width='stretch', config=config)

        with batch_tabs[3]:
            st.header("Integral Comparison")
            st.plotly_chart(plot_batch_comparison(runs, "Integral"), width='stretch', config=config)

        with batch_tabs[4]:
            st.header("Phase Portraits")
            st.markdown("Spectral phase portraits (Width vs AEW) for all runs. Green = start, Red = end. Time shown by color gradient.")
            st.plotly_chart(plot_batch_phase_portraits(runs), width='stretch', config=config)

        with batch_tabs[5]:
            st.header("Metrics Summary")
            summary_df = create_batch_metrics_summary(runs)
            if not summary_df.empty:
                st.dataframe(summary_df, width='stretch')

        with batch_tabs[6]:
            st.header("Export")

            # Excel export
            excel_data = save_batch_to_excel(runs)
            if excel_data:
                st.download_button("📥 Download All as Excel", data=excel_data, file_name="batch_export.xlsx",
                                  mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            st.markdown("---")

            # Tidy CSV export with provenance
            st.subheader("Tidy CSV Export")
            st.markdown("Export all runs in tidy format with provenance metadata. Ideal for downstream analysis in Python, R, or Excel.")

            # Collect analysis parameters for provenance
            analysis_params = {
                'blank_subtraction_mode': 'per-run',
            }

            tidy_csv = export_tidy_csv_with_provenance(runs, analysis_params)
            if tidy_csv:
                st.download_button(
                    "📊 Download Tidy CSV (with provenance)",
                    data=tidy_csv.encode('utf-8'),
                    file_name="batch_metrics_tidy.csv",
                    mime='text/csv',
                    help="CSV file with one row per timepoint, columns: run, process_time_h, aew_nm, integral, max_wavelength_nm"
                )

                # Preview
                with st.expander("Preview tidy data"):
                    preview_lines = tidy_csv.split('\n')[:15]
                    st.code('\n'.join(preview_lines), language='csv')
