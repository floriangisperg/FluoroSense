import streamlit as st
st.set_page_config(layout="wide")
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import io
from io import StringIO
from io import BytesIO
from openpyxl import Workbook
from openpyxl.writer.excel import save_workbook
from tempfile import NamedTemporaryFile

# plot settings:
width = 1250
height = 750
template = "seaborn" # 'ggplot2', 'seaborn', 'simple_white', 'plotly',
         # 'plotly_white', 'plotly_dark', 'presentation', 'xgridoff',
         # 'ygridoff', 'gridon', 'none'
download_width = 1250
download_height = 750
download_text_scale = 1
config = {'displaylogo': False,
           'toImageButtonOptions': { # download settings
                'format': 'svg', # one of png, svg, jpeg, webp
                'filename': 'plot',
                'height': download_height,
                'width': download_width,
                'scale': download_text_scale }, # Multiply title/legend/axis/canvas sizes by this factor
           'modeBarButtonsToAdd': ['hoverclosest', 'hovercompare', 'togglehover', 'togglespikelines',
                                    'v1hovermode',
                                    'drawline',
                                    'drawopenpath',
                                    'drawclosedpath',
                                    'drawcircle',
                                    'drawrect',
                                    'eraseshape'
                                       ],
          'displayModeBar': True}

@st.cache_data
def upload_jasco_rawdata(uploaded_file):
    """
    Improved function to parse Jasco raw data files with extended information section
    """
    header = {}
    xydata = []
    extended_info = {}

    lines = uploaded_file.readlines()
    mode = 'header'
    data_started = False
    data_ended = False
    
    for line in lines:
        line = line.decode().strip()  # decode byte stream to string
        
        # Check for XYDATA section
        if line.startswith('XYDATA'):
            mode = 'data'
            data_started = False  # Reset flag until we see the actual data headers
            continue
            
        # Check for Extended Information section
        if line.startswith('##### Extended Information'):
            mode = 'extended'
            data_ended = True
            continue
            
        # Process based on current mode
        if mode == 'header':
            if ',' in line:  # Ensure there's a comma to split
                parts = line.split(',', 1)
                if len(parts) == 2:
                    key, value = parts
                    header[key] = value.rstrip(',')
        
        elif mode == 'data':
            # Skip empty lines
            if not line or line.isspace():
                continue
                
            # Skip lines starting with #####
            if line.startswith('#####'):
                mode = 'extended'
                data_ended = True
                continue
                
            # If we hit a line with the data headers, mark data as started
            if not data_started and ',' in line and not line.startswith('#'):
                data_started = True
                xydata.append(line.split(','))
                continue
                
            # Process actual data lines
            if data_started and not data_ended:
                fields = line.split(',')
                if len(fields) >= 2:  # Ensure there's enough data
                    xydata.append(fields)
        
        elif mode == 'extended':
            if ',' in line:
                parts = line.split(',', 1)
                if len(parts) == 2:
                    key, value = parts
                    extended_info[key.strip()] = value.strip()

    # Process the collected data rows into a DataFrame
    if xydata and len(xydata) > 1:  # Ensure we have headers and at least one data row
        try:
            # Create DataFrame from the data
            df = pd.DataFrame(xydata[1:], columns=xydata[0])
            
            # Convert all columns to numeric if possible
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Handle first column as index if it's unnamed
            try:
                if '' in df.columns:
                    df.set_index('', inplace=True)
                elif df.columns[0].strip() == '':
                    df.set_index(df.columns[0], inplace=True)
            except Exception as e:
                # If we can't set the index, just continue with the DataFrame as is
                pass
                
            # Clean up DataFrame - drop NaN rows at the end (which might come from extended info)
            df = df.dropna(how='all')
            
        except Exception as e:
            st.error(f"Error processing data: {str(e)}")
            df = pd.DataFrame()
    else:
        df = pd.DataFrame()
        
    return header, df, extended_info

def subtract_blank_from_time_series(df, blank_method='timepoint', blank_timepoint=None, blank_start=None, blank_end=None):
    """
    Subtract a blank spectrum from all spectra in a time series
    
    Args:
        df: DataFrame with wavelengths as index and time points as columns
        blank_method: 'timepoint' for single timepoint, 'average' for average of time range
        blank_timepoint: Column name (timepoint) to use as blank if blank_method is 'timepoint'
        blank_start: Starting timepoint for average if blank_method is 'average'
        blank_end: Ending timepoint for average if blank_method is 'average'
        
    Returns:
        DataFrame with blank subtracted from all columns
    """
    # Make a copy of the input DataFrame to avoid modifying the original
    result_df = df.copy()
    
    try:
        # Convert all columns to numeric
        for col in result_df.columns:
            result_df[col] = pd.to_numeric(result_df[col], errors='coerce')
        
        # Get the blank spectrum based on method
        if blank_method == 'timepoint' and blank_timepoint:
            if blank_timepoint in result_df.columns:
                blank_spectrum = result_df[blank_timepoint]
            else:
                st.error(f"Specified blank timepoint {blank_timepoint} not found in data")
                return df
        
        elif blank_method == 'average' and blank_start and blank_end:
            # Get all columns between blank_start and blank_end
            cols_between = [col for col in result_df.columns 
                           if pd.to_numeric(col, errors='coerce') >= pd.to_numeric(blank_start, errors='coerce') 
                           and pd.to_numeric(col, errors='coerce') <= pd.to_numeric(blank_end, errors='coerce')]
            
            if cols_between:
                blank_spectrum = result_df[cols_between].mean(axis=1)
            else:
                st.error(f"No columns found between {blank_start} and {blank_end}")
                return df
        else:
            st.error("Invalid blank subtraction parameters")
            return df
        
        # Subtract the blank spectrum from each column
        for col in result_df.columns:
            result_df[col] = result_df[col] - blank_spectrum
        
        # Store that blank subtraction was applied (for file naming)
        st.session_state['blank_subtraction_applied'] = True
        
        return result_df
        
    except Exception as e:
        st.error(f"Error during blank subtraction: {str(e)}")
        return df

def blank_subtraction_ui(df):
    """
    Create UI elements for blank subtraction in Time Series
    
    Args:
        df: DataFrame with wavelengths as index and time points as columns
        
    Returns:
        DataFrame (either original or with blank subtracted)
    """
    st.sidebar.markdown("## Blank Subtraction")
    use_blank = st.sidebar.checkbox("Apply Blank Subtraction", False)
    
    # Reset flag if not using blank subtraction
    if not use_blank:
        st.session_state['blank_subtraction_applied'] = False
        return df
    
    # Convert columns to numeric and sort them
    numeric_columns = []
    for col in df.columns:
        try:
            numeric_columns.append(float(col))
        except ValueError:
            continue
    
    numeric_columns.sort()
    
    # Convert back to strings for selection
    column_options = [str(col) for col in numeric_columns]
    
    if not column_options:
        st.sidebar.warning("No numeric column names found for blank selection")
        return df
    
    blank_method = st.sidebar.radio(
        "Blank Subtraction Method",
        ["Single Timepoint", "Average of Range"],
        index=0
    )
    
    if blank_method == "Single Timepoint":
        blank_timepoint = st.sidebar.selectbox(
            "Select timepoint to use as blank",
            column_options,
            index=0
        )
        
        # Preview the selected blank
        if st.sidebar.checkbox("Preview Blank Spectrum", False):
            try:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df.index,
                    y=df[blank_timepoint],
                    mode='lines',
                    name=f'Blank Spectrum (t={blank_timepoint})'
                ))
                fig.update_layout(
                    title="Selected Blank Spectrum",
                    xaxis_title="Wavelength [nm]",
                    yaxis_title="Intensity"
                )
                st.sidebar.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.sidebar.error(f"Error previewing blank: {str(e)}")
        
        result_df = subtract_blank_from_time_series(
            df, 
            blank_method='timepoint',
            blank_timepoint=blank_timepoint
        )
        
    else:  # Average of Range
        col1, col2 = st.sidebar.columns(2)
        with col1:
            blank_start = st.selectbox(
                "Start timepoint",
                column_options,
                index=0
            )
        with col2:
            # Find index of start point and set end to start+3 by default (if possible)
            start_index = column_options.index(blank_start)
            default_end_index = min(start_index + 3, len(column_options) - 1)
            
            blank_end = st.selectbox(
                "End timepoint",
                column_options,
                index=default_end_index
            )
        
        # Preview the average blank
        if st.sidebar.checkbox("Preview Average Blank Spectrum", False):
            try:
                # Get all columns between blank_start and blank_end
                cols_between = [col for col in df.columns 
                               if pd.to_numeric(col, errors='coerce') >= float(blank_start) 
                               and pd.to_numeric(col, errors='coerce') <= float(blank_end)]
                
                if cols_between:
                    avg_blank = df[cols_between].mean(axis=1)
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df.index,
                        y=avg_blank,
                        mode='lines',
                        name=f'Average Blank ({blank_start}-{blank_end})'
                    ))
                    fig.update_layout(
                        title="Average Blank Spectrum",
                        xaxis_title="Wavelength [nm]",
                        yaxis_title="Intensity"
                    )
                    st.sidebar.plotly_chart(fig, use_container_width=True)
                else:
                    st.sidebar.warning("No columns found in selected range")
            except Exception as e:
                st.sidebar.error(f"Error previewing average blank: {str(e)}")
        
        result_df = subtract_blank_from_time_series(
            df, 
            blank_method='average',
            blank_start=blank_start,
            blank_end=blank_end
        )
    
    # Option to download the blank-subtracted data
    if st.session_state.get('blank_subtraction_applied', False):
        st.sidebar.success("Blank subtraction applied!")
        
        # Create download button for blank-subtracted data
        csv = result_df.to_csv(sep='\t').encode('utf-8')
        st.sidebar.download_button(
            label="Download Blank-Subtracted Data as .txt",
            data=csv,
            file_name="blank_subtracted_data.txt",
            mime='text/plain',
        )
    
    return result_df

def preprocess_time_series_data(df):
    """Clean and prepare time series data"""
    # If the DataFrame is empty, return it as is
    if df.empty:
        return df
        
    # Get data types for columns
    dtypes = df.dtypes
    
    # Keep only numeric columns
    numeric_cols = dtypes[dtypes.apply(lambda x: pd.api.types.is_numeric_dtype(x))].index
    numeric_df = df[numeric_cols]
    
    # If we have no numeric columns, try to convert all to numeric
    if numeric_df.empty:
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        numeric_df = df.select_dtypes(include=['number'])
        
    # Try to ensure index is numeric
    try:
        numeric_df.index = pd.to_numeric(numeric_df.index, errors='coerce')
    except:
        pass
        
    # Drop any rows with all NaN values
    numeric_df = numeric_df.dropna(how='all')
    
    # Drop any columns with all NaN values
    numeric_df = numeric_df.dropna(axis=1, how='all')
    
    return numeric_df

def calculate_integrals(df):
    """Calculate integrals for each column in the dataframe"""
    try:
        # Make sure df is properly formatted
        numeric_df = df.select_dtypes(include=['number'])
        
        if numeric_df.empty:
            return pd.Series(dtype=float)
        
        # Ensure index is numeric
        try:
            if not pd.api.types.is_numeric_dtype(numeric_df.index):
                numeric_df.index = pd.to_numeric(numeric_df.index, errors='coerce')
                
            # Sort index to ensure proper integration
            numeric_df = numeric_df.sort_index().dropna(how='all')
        except Exception as e:
            st.error(f"Error preparing data for integration: {str(e)}")
            return pd.Series(dtype=float)
        
        # Calculate trapezoid rule for each column
        return numeric_df.apply(lambda col: np.trapz(col, x=numeric_df.index), axis=0)
    except Exception as e:
        st.error(f"Error calculating integrals: {str(e)}")
        return pd.Series(dtype=float)

def calculate_avg_emission_wavelength(df):
    """Calculate average emission wavelength for each spectrum"""
    try:
        # Make sure df is properly formatted
        numeric_df = df.select_dtypes(include=['number'])
        
        if numeric_df.empty:
            return []
            
        # Ensure index is numeric
        if not pd.api.types.is_numeric_dtype(numeric_df.index):
            numeric_df.index = pd.to_numeric(numeric_df.index, errors='coerce')
        numeric_df = numeric_df.sort_index().dropna(how='all')
        
        avg_emission_wavelength = []
        
        for col in numeric_df.columns:
            try:
                # Skip columns with zero or negative values
                if (numeric_df[col] <= 0).all():
                    avg_emission_wavelength.append(np.nan)
                    continue
                    
                # Calculate weighted average
                weighted_sum = np.sum(numeric_df.index * numeric_df[col])
                total_intensity = np.sum(numeric_df[col])
                
                if total_intensity > 0:  # Avoid division by zero
                    avg_emission_wavelength.append(weighted_sum / total_intensity)
                else:
                    avg_emission_wavelength.append(np.nan)
            except Exception as e:
                st.warning(f"Could not calculate AEW for column {col}: {str(e)}")
                avg_emission_wavelength.append(np.nan)
                
        return avg_emission_wavelength
    except Exception as e:
        st.error(f"Error calculating average emission wavelengths: {str(e)}")
        return []
    
def calculate_max_emission_wavelength(df):
    """Find wavelength with maximum intensity for each spectrum"""
    try:
        # Make sure df is properly formatted
        numeric_df = df.select_dtypes(include=['number'])
        
        if numeric_df.empty:
            return []
            
        # Ensure index is numeric
        if not pd.api.types.is_numeric_dtype(numeric_df.index):
            numeric_df.index = pd.to_numeric(numeric_df.index, errors='coerce')
        numeric_df = numeric_df.sort_index().dropna(how='all')
        
        max_emission_wavelength = []
        
        for col in numeric_df.columns:
            try:
                max_wavelength = numeric_df.index[np.argmax(numeric_df[col])]
                max_emission_wavelength.append(max_wavelength)
            except Exception as e:
                st.warning(f"Could not calculate max wavelength for column {col}: {str(e)}")
                max_emission_wavelength.append(np.nan)
                
        return max_emission_wavelength
    except Exception as e:
        st.error(f"Error calculating max emission wavelengths: {str(e)}")
        return []

def augment_dataframe(df, avg_emission_wavelength, integrals, max_emission_wavelength):
    """Combine all calculated metrics into a processed dataframe"""
    try:
        df_transposed = df.transpose()
        df_transposed_aew = df_transposed.copy()
        df_transposed_aew["Average emission wavelength [nm]"] = avg_emission_wavelength
        df_transposed_aew_integral = df_transposed_aew.copy()
        df_transposed_aew_integral["Integral"] = integrals
        df_transposed_aew_integral["Max emission wavelength [nm]"] = max_emission_wavelength     
        df_transposed_aew_integral.reset_index(inplace = True)
        df_transposed_aew_integral.rename(columns={df_transposed_aew_integral.columns[0]: "Process Time [min]"}, inplace=True)
        df_transposed_aew_integral["Process Time [min]"] = pd.to_numeric(df_transposed_aew_integral["Process Time [min]"], errors='coerce')
        df_transposed_aew_integral["Process Time [h]"] = round(df_transposed_aew_integral["Process Time [min]"] / 60, 3)
        return df_transposed, df_transposed_aew_integral
    except Exception as e:
        st.error(f"Error creating augmented dataframe: {str(e)}")
        # Return empty dataframes to avoid breaking downstream functions
        return pd.DataFrame(), pd.DataFrame(columns=["Process Time [min]", "Process Time [h]", 
                                                   "Average emission wavelength [nm]", 
                                                   "Integral", "Max emission wavelength [nm]"])

def closest_times(df, interval):
    """Find closest times for selected interval"""
    try:
        available_times = df['Process Time [h]'].values
        interval_times = np.arange(0, available_times.max() + interval, interval)
        closest_indices = []
        
        for t in interval_times:
            idx = np.abs(available_times - t).argmin()
            if idx not in closest_indices:
                closest_indices.append(idx)
                
        return df.iloc[closest_indices]
    except Exception as e:
        st.error(f"Error finding closest times: {str(e)}")
        return df

@st.cache_data
def plot_data(df, y_column, template=template, width=width, height=height, config=config):
    """Create scatter plot for selected metric over time"""
    try:
        fig = px.scatter(df, x="Process Time [h]", y=y_column, template=template)
        fig.update_layout(autosize=False, width=width, height=height)
        return fig
    except Exception as e:
        st.error(f"Error creating plot: {str(e)}")
        fig = go.Figure()
        fig.update_layout(
            title=f"Error creating plot: {str(e)}",
            xaxis_title="Process Time [h]",
            yaxis_title=y_column
        )
        return fig
         
@st.cache_data
def plot_intensity(df, interval=None, template=template, width=width, height=height, config=config):
    """Plot intensity spectra for selected time points"""
    try:
        if interval is not None:
            df = closest_times(df, interval)
            df = df.reset_index(drop=True)

        df_plot = df.T
        df_plot.columns = df_plot.iloc[-1]
        df_plot = df_plot[:-4]  # Remove the last 4 rows which contain the metrics

        fig = go.Figure()

        for i in range(df_plot.shape[1]):
            fig.add_trace(
                go.Scatter(
                    x=df_plot.index,
                    y=df_plot[df_plot.columns[i]],
                    name=str(df_plot.columns[i]),
                    customdata=np.tile(df_plot.columns[i], len(df_plot.index)),
                    hovertemplate=
                    '<b>Process Time [h]:</b> %{customdata}<br>' +
                    '<b>Wavelength [nm]:</b> %{x}<br>' +
                    '<b>Intensity:</b> %{y}<extra></extra>',
                ))

        fig.update_layout(
            width=width,
            height=height,
            template=template,
            xaxis_title="Wavelength [nm]",
            yaxis_title="Intensity",
            legend_title="Process Time [h]"
        )

        return fig
    except Exception as e:
        st.error(f"Error creating intensity plot: {str(e)}")
        fig = go.Figure()
        fig.update_layout(
            title=f"Error creating intensity plot: {str(e)}",
            xaxis_title="Wavelength [nm]",
            yaxis_title="Intensity"
        )
        return fig

@st.cache_data
def plot_contour(df, ncontours=15, template=template, width=width, height=height, config=config):
    """Create contour plot visualization"""
    try:
        # Make sure df is properly formatted
        numeric_df = df.select_dtypes(include=['number'])
        
        if numeric_df.empty:
            st.error("No numeric data available for contour plot")
            fig = go.Figure()
            fig.update_layout(
                title="No data available for contour plot",
                xaxis_title='Wavelength [nm]',
                yaxis_title='Time'
            )
            return fig
            
        # Convert index to numeric if needed
        if not pd.api.types.is_numeric_dtype(numeric_df.index):
            numeric_df.index = pd.to_numeric(numeric_df.index, errors='coerce')
            
        # Sort by index
        numeric_df = numeric_df.sort_index().dropna(how='all')
        
        # Convert data to arrays for plotting
        Z = numeric_df.to_numpy()
        X = np.array(numeric_df.index, dtype=float)  # Wavelengths (index)
        Y = np.array(numeric_df.columns, dtype=float)  # Time points (columns)
        
        # Create contour plot
        fig = go.Figure(data=
            go.Contour(
                z=Z,
                x=X,  # X is wavelength (index)
                y=Y,  # Y is time (columns)
                colorscale='Viridis',
                hovertemplate='Wavelength [nm]: %{x}<br>Time: %{y}<br>Intensity: %{z}<extra></extra>',
                ncontours=ncontours,
                colorbar=dict(title="Intensity")
            ))
            
        fig.update_layout(
            xaxis_title='Wavelength [nm]',
            yaxis_title='Time',
            autosize=False,
            width=width,
            height=height,
            template=template
        )
        
        return fig
    except Exception as e:
        st.error(f"Error creating contour plot: {str(e)}")
        fig = go.Figure()
        fig.update_layout(
            title=f"Error creating contour plot: {str(e)}",
            xaxis_title='Wavelength [nm]',
            yaxis_title='Time'
        )
        return fig

@st.cache_data
def save_to_excel(header, df, engine='xlsxwriter'):
    """Save processed data to Excel file"""
    try:
        header_df = pd.DataFrame.from_dict(header, orient='index', columns=['Value'])

        # Create a BytesIO buffer
        output = BytesIO()

        # Create a Pandas ExcelWriter using the buffer and the specified engine
        with pd.ExcelWriter(output, engine=engine) as writer:
            # Write each dataframe to a different worksheet
            df.to_excel(writer, sheet_name='Data', index=False)
            header_df.to_excel(writer, sheet_name='Info')

        # Reset the buffer position to the beginning
        output.seek(0)

        # Return the contents of the buffer
        return output.getvalue()
    except Exception as e:
        st.error(f"Error saving to Excel: {str(e)}")
        # Return empty bytes to avoid breaking the app
        return b''

@st.cache_data
def df_to_txt(df, y_column):
    """Convert dataframe to tab-separated text for download"""
    try:
        df_subset = df[["Process Time [h]", y_column]]
        str_io = StringIO()
        df_subset.to_csv(str_io, sep='\t', index=False)
        return str_io.getvalue()
    except Exception as e:
        st.error(f"Error converting to TXT: {str(e)}")
        return ""

# Initialize session state for blank subtraction flag if not exists
if 'blank_subtraction_applied' not in st.session_state:
    st.session_state['blank_subtraction_applied'] = False

# Main application flow
with st.expander("Upload file here"):
    uploaded_file = st.sidebar.file_uploader("Choose CSV file")

if uploaded_file:
    header, df, extended_info = upload_jasco_rawdata(uploaded_file)
    
    # Add debugging info (optional but helpful)
    with st.sidebar.expander("Debug Information", expanded=False):
        st.write("DataFrame Shape:", df.shape)
        st.write("DataFrame Columns:", df.columns.tolist()[:10] + (["..."] if len(df.columns) > 10 else []))
        st.write("DataFrame Index Type:", type(df.index))
        st.write("Extended Info Keys:", list(extended_info.keys()) if extended_info else "None")
    
    # Clean up the data
    df = preprocess_time_series_data(df)
    
    # Apply blank subtraction if requested
    df = blank_subtraction_ui(df)
    
    # Calculate metrics
    integrals = calculate_integrals(df)
    avg_emission_wavelength = calculate_avg_emission_wavelength(df)
    max_emission_wavelength = calculate_max_emission_wavelength(df)
    df_transposed, df_augmented = augment_dataframe(df, avg_emission_wavelength, integrals, max_emission_wavelength)

    # Add file suffix if blank subtraction was applied
    file_suffix = "_blank_subtracted" if st.session_state.get('blank_subtraction_applied', False) else ""
    
    # Download buttons
    excel_data = save_to_excel(header, df_augmented)
    st.sidebar.download_button(
        label="Download processed Data as Excel-File",
        data=excel_data,
        file_name=header.get("TITLE", "data") + "_processed" + file_suffix + ".xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
         
    aew_df_txt = df_to_txt(df_augmented, "Average emission wavelength [nm]")
    st.sidebar.download_button(
        label="AEW as .txt",
        data= aew_df_txt,
        file_name= header.get("TITLE", "data") + "_aew" + file_suffix + ".txt",
        mime='text/csv',
    )
    
    intensity_df_txt = df_to_txt(df_augmented, "Integral")
    st.sidebar.download_button(
        label="Intensity as .txt",
        data=intensity_df_txt,
        file_name=header.get("TITLE", "data") + "_intensity" + file_suffix + ".txt",
        mime='text/csv',
    )
    
    max_wavelength_df_txt = df_to_txt(df_augmented, "Max emission wavelength [nm]")
    st.sidebar.download_button(
         label="Max Wavelength as .txt",
         data=max_wavelength_df_txt,
         file_name=header.get("TITLE", "data") + "_max_wavelength" + file_suffix + ".txt",
         mime='text/csv',
    )

    # Display header info in sidebar
    if header:
        st.sidebar.write("---")
        for key, value in header.items():
            st.sidebar.text(f"{key}: {value}")

    # Add info about blank subtraction if applied
    if st.session_state.get('blank_subtraction_applied', False):
        st.info("Note: Blank subtraction has been applied to all spectra.")
        
    # Create tabs for different visualizations
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Experiment all","Average Emission Wavelength", "Max Emission Wavelength", "Integral of Intensities", "Contour"])

    with tab1:
        # Add a slider to select time interval
        interval = st.select_slider(
            'Select time interval of plotted graphs',
            options=[None, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2], value = 0.25)
        
        # Plot intensity with selected interval
        fig = plot_intensity(df_augmented, interval=interval)
        # Show the plot
        st.plotly_chart(fig, use_container_width=True, theme=None, **{"config": config})

    with tab2:
       st.header("Average emission wavelength [nm]")
       fig = plot_data(df_augmented, "Average emission wavelength [nm]")
       st.plotly_chart(fig, use_container_width=True, theme=None, **{"config": config})

    with tab3:
       st.header("Max Emission Wavelength [nm]")
       fig = plot_data(df_augmented, "Max emission wavelength [nm]")
       st.plotly_chart(fig, use_container_width=True, theme=None, **{"config": config})

    with tab4:
       st.header("Integral of the intensity")
       fig = plot_data(df_augmented, "Integral")
       st.plotly_chart(fig, use_container_width=True, theme=None, **{"config": config})

    with tab5:
       st.header("Contour plot")
       fig = plot_contour(df_transposed) #ncontours=15)
       st.plotly_chart(fig, use_container_width=True, theme=None, **{"config": config})
