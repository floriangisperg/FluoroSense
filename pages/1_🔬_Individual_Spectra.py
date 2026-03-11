"""
FluoroSense - Individual Spectra Analysis
Dark Lab Theme Applied
"""
import streamlit as st

# Page config must be first
st.set_page_config(
    layout="wide",
    page_title="Individual Spectra",
    page_icon="🔬"
)

from styles import apply_dark_lab_theme, get_plotly_dark_template, EMISSION_PALETTE

# Apply theme after page config
apply_dark_lab_theme()

import plotly.graph_objects as go
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import pandas as pd
from scipy.integrate import simpson

# Plot settings - Dark Lab theme
width = 1200
height = 600
download_width = 1200
download_height = 600
download_text_scale = 1

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

# Dark template for Plotly
dark_template = get_plotly_dark_template()


def upload_jasco_rawdata(uploaded_file):
    header = {}
    xydata = []
    extended_info = {}

    lines = uploaded_file.readlines()
    mode = 'header'
    for line in lines:
        line = line.decode().strip()
        if line.startswith('XYDATA'):
            mode = 'data'
            continue
        if line == '##### Extended Information':
            mode = 'extended'
            continue
        if mode == 'header':
            key, value = line.split(',', 1)
            header[key] = value.rstrip(',')
        elif mode == 'data':
            if not line.startswith('#####'):
                fields = line.split(',')
                xydata.append(fields)
            else:
                mode = 'extended'
        elif mode == 'extended':
            if ',' in line:
                key, value = line.split(',', 1)
                extended_info[key.strip()] = value.strip()

    if xydata:
        df = pd.DataFrame(xydata[1:], columns=xydata[0])
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        try:
            df.set_index('', inplace=True)
        except:
            df = df.iloc[:-1]
            df.columns = ["Wavelength [nm]", "Intensity"]
    else:
        df = pd.DataFrame()

    return header, df, extended_info


def single_measurement_df_to_txt(df, header, suffix=''):
    csv = df.to_csv(sep='\t', index=False).encode('utf-8')
    return csv


def convert_df_to_txt(df, header):
    txt = single_measurement_df_to_txt(df, header)
    return txt.encode('utf-8')


def subtract_blank(sample_df, blank_df):
    if blank_df.empty:
        return sample_df
    corrected_df = sample_df.copy()
    corrected_df['Intensity'] = sample_df['Intensity'] - blank_df['Intensity'].values
    return corrected_df


@st.cache_data
def calculate_avg_emission_wavelength(df):
    weighted_sum = np.sum(df["Wavelength [nm]"] * df["Intensity"])
    total_intensity = np.sum(df["Intensity"])
    avg_emission_wavelength = weighted_sum / total_intensity
    return avg_emission_wavelength


def download_data(data_headers_and_dfs, suffix=''):
    for header, df, extended_info in data_headers_and_dfs:
        csv = single_measurement_df_to_txt(df, header, suffix)
        st.download_button(
            label=f"Download {header['TITLE']}{suffix} as .txt",
            data=csv,
            file_name=f"{header['TITLE']}{suffix}.txt",
            mime='text/plain',
        )


@st.cache_data
def normalize(df):
    scaler = MinMaxScaler()
    cols_to_scale = df.columns.difference(['Wavelength [nm]'])
    scaled_cols = pd.DataFrame(scaler.fit_transform(df[cols_to_scale]),
                               columns=cols_to_scale,
                               index=df.index)
    df_normalized = pd.concat([df['Wavelength [nm]'], scaled_cols], axis=1)
    return df_normalized


def calculate_integral(df):
    return simpson(df["Intensity"], df["Wavelength [nm]"])


def plot_data(data_headers_and_dfs):
    fig = go.Figure()

    for i, (header, df, extended_info) in enumerate(data_headers_and_dfs):
        color = EMISSION_PALETTE[i % len(EMISSION_PALETTE)]
        fig.add_trace(go.Scatter(
            x=df["Wavelength [nm]"],
            y=df["Intensity"],
            name=header['TITLE'],
            customdata=np.tile(header['TITLE'], len(df.index)),
            hovertemplate='<b>%{customdata}</b><br>WL: %{x} nm<br>Intensity: %{y}<extra></extra>',
            line=dict(color=color, width=2),
            marker=dict(color=color)
        ))

    fig.update_layout(
        **dark_template['layout'],
        width=width,
        height=height,
        xaxis_title="Wavelength [nm]",
        yaxis_title="Intensity",
        legend_title="Experiment"
    )

    st.plotly_chart(fig, width='stretch', config=config)


def plot_bar_chart(df, x_col, y_col, title):
    fig = go.Figure(data=[
        go.Bar(
            name=title,
            x=df[x_col],
            y=df[y_col],
            marker_color=EMISSION_PALETTE[:len(df)],
            hovertemplate=f'<b>%{{x}}</b><br>{title}: %{{y}}<extra></extra>',
        )
    ])

    fig.update_layout(
        **dark_template['layout'],
        width=width,
        height=height,
        xaxis_title="Experiment",
        yaxis_title=title,
        showlegend=False
    )

    st.plotly_chart(fig, width='stretch', config=config)


def main():
    # Page header
    st.title("Individual Spectra Analysis")
    st.markdown("Upload Jasco spectrofluorometer CSV files to analyze individual emission spectra.")

    # Sidebar
    st.sidebar.header("Data Upload")

    # File uploader for sample files
    uploaded_files = st.sidebar.file_uploader("Choose CSV files", accept_multiple_files=True)

    # Blank file section
    st.sidebar.markdown("---")
    st.sidebar.subheader("Blank Subtraction")
    blank_file = st.sidebar.file_uploader("Upload blank file", accept_multiple_files=False)
    use_blank = st.sidebar.checkbox("Subtract Blank", False)

    if use_blank and blank_file:
        st.sidebar.success("Blank subtraction enabled")
    elif use_blank and not blank_file:
        st.sidebar.warning("Upload a blank file")

    # Process the blank file
    blank_header, blank_df, blank_extended_info = (None, pd.DataFrame(), None)
    if blank_file is not None:
        blank_header, blank_df, blank_extended_info = upload_jasco_rawdata(blank_file)

    # Process the sample files
    data_headers_and_dfs = []
    for file in uploaded_files:
        header, df, extended_info = upload_jasco_rawdata(file)
        if use_blank:
            df = subtract_blank(df, blank_df)
        data_headers_and_dfs.append((header, df, extended_info))

    if data_headers_and_dfs:
        # Check for duplicate headers
        titles = [header['TITLE'] for header, df, extended_info in data_headers_and_dfs]
        if len(titles) != len(set(titles)):
            st.warning("Duplicate files detected. Please upload only unique files.")
        else:
            # Display file info
            with st.expander("File Information", expanded=False):
                for header, df, extended_info in data_headers_and_dfs:
                    st.markdown(f"**{header.get('TITLE', 'Unknown')}**")
                    cols = st.columns(3)
                    cols[0].metric("Data Points", len(df))
                    cols[1].metric("WL Range", f"{df['Wavelength [nm]'].min():.1f} - {df['Wavelength [nm]'].max():.1f} nm")
                    cols[2].metric("Max Intensity", f"{df['Intensity'].max():.1f}")

            # Tabs
            tab1, tab2, tab3, tab4 = st.tabs([
                "Raw Data",
                "Average Emission Wavelength",
                "Integral",
                "Normalized Data"
            ])

            with tab1:
                st.subheader("Emission Spectra")
                plot_data(data_headers_and_dfs)
                download_data(data_headers_and_dfs)

            with tab2:
                st.subheader("Average Emission Wavelength")
                st.markdown("The AEW represents the intensity-weighted center of mass of the emission spectrum.")

                avg_emission_wavelength = [
                    (header['TITLE'], calculate_avg_emission_wavelength(df))
                    for header, df, extended_info in data_headers_and_dfs
                ]
                avg_emission_df = pd.DataFrame(
                    avg_emission_wavelength,
                    columns=["Title", "Average Emission Wavelength"]
                )

                st.dataframe(avg_emission_df, width='stretch', hide_index=True)

                # Download button
                avg_emission_csv = avg_emission_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download AEW data as CSV",
                    data=avg_emission_csv,
                    file_name='average_emission_wavelength.csv',
                    mime='text/csv',
                )

                # Bar chart
                plot_bar_chart(avg_emission_df, "Title", "Average Emission Wavelength", "AEW [nm]")

            with tab3:
                st.subheader("Spectral Integral")
                st.markdown("The integral represents the total fluorescence intensity across all wavelengths.")

                integrals = [
                    (header['TITLE'], calculate_integral(df))
                    for header, df, extended_info in data_headers_and_dfs
                ]
                integrals_df = pd.DataFrame(integrals, columns=["Title", "Integral"])

                st.dataframe(integrals_df, width='stretch', hide_index=True)

                # Download button
                integrals_csv = integrals_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download integrals as CSV",
                    data=integrals_csv,
                    file_name='integrals.csv',
                    mime='text/csv',
                )

                # Bar chart
                plot_bar_chart(integrals_df, "Title", "Integral", "Integral")

            with tab4:
                st.subheader("Normalized Spectra")
                st.markdown("Spectra normalized to [0, 1] range for shape comparison.")

                data_headers_and_dfs_normalized = [
                    (header, normalize(df), extended_info)
                    for header, df, extended_info in data_headers_and_dfs
                ]
                plot_data(data_headers_and_dfs_normalized)
                download_data(data_headers_and_dfs_normalized, suffix='_normalized')


if __name__ == "__main__":
    main()
