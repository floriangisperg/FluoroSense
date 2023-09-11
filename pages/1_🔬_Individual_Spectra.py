from pages.2_⏳_Time_Series_Measurement import upload_jasco_rawdata
import streamlit as st
st.set_page_config(layout="wide")
import plotly.graph_objects as go
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import pandas as pd
from scipy.integrate import simps


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
                                    'v1hovermode'
                                    'drawline',
                                    'drawopenpath',
                                    'drawclosedpath',
                                    'drawcircle',
                                    'drawrect',
                                    'eraseshape'
                                       ],
          'displayModeBar': True}

def single_measurement_df_to_txt(df, header, suffix=''):
    csv = df.to_csv(sep='\t', index=False).encode('utf-8')
    return csv
@st.cache_data
def file_uploader():
    uploaded_files = st.sidebar.file_uploader("Choose one or multiple CSV files", accept_multiple_files=True)
    data_headers_and_dfs = [upload_jasco_rawdata(file) for file in uploaded_files]
    return data_headers_and_dfs

def convert_df_to_txt(df, header):
    txt = single_measurement_df_to_txt(df, header)
    return txt.encode('utf-8')  # Encode as byte stream for download
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

    # Select the columns to scale
    cols_to_scale = df.columns.difference(['Wavelength [nm]'])

    # Scale those columns
    scaled_cols = pd.DataFrame(scaler.fit_transform(df[cols_to_scale]),
                               columns=cols_to_scale,
                               index=df.index)

    # Concatenate the scaled columns with the ones that weren't scaled
    df_normalized = pd.concat([df['Wavelength [nm]'], scaled_cols], axis=1)

    return df_normalized
         
def calculate_integral(df):
    return simps(df["Intensity"], df["Wavelength [nm]"])
         
def plot_data(data_headers_and_dfs, template=template, width=width, height=height, config=config):
    fig = go.Figure()

    for i, (header, df, extended_info) in enumerate(data_headers_and_dfs):
        fig.add_trace(
            go.Scatter(
                x=df["Wavelength [nm]"],
                y=df["Intensity"],
                name=header['TITLE'],
                customdata=np.tile(header['TITLE'], len(df.index)),
                hovertemplate=
                '<b>Title:</b> %{customdata}<br>' +
                '<b>Wavelength [nm]:</b> %{x}<br>' +
                '<b>Intensity:</b> %{y}<extra></extra>',
            ))

    fig.update_layout(
        width=width,
        height=height,
        template=template,
        xaxis_title="Wavelength [nm]",
        yaxis_title="Intensity",
        legend_title="Experiment"
    )

    st.plotly_chart(fig, use_container_width=True, theme=None, **{"config": config})

def main():
    uploaded_files = st.sidebar.file_uploader("Choose CSV files", accept_multiple_files=True)
    data_headers_and_dfs = [upload_jasco_rawdata(file) for file in uploaded_files]

    if data_headers_and_dfs:
        # Check for duplicate headers
        titles = [header['TITLE'] for header, df, extended_info in data_headers_and_dfs]
        if len(titles) != len(set(titles)):
            st.warning("Duplicate files detected. Please upload only unique files.")
        else:
            tab1, tab2, tab3, tab4 = st.tabs(["Raw Data Visualization", "Average Emission Wavelength", "Integral", "Normalized Data"])

            with tab1:
                #st.write("Dataframes loaded successfully. Ready for visualization.")
                plot_data(data_headers_and_dfs)
                #st.write("Visualization complete. Ready for download.")
                download_data(data_headers_and_dfs)

            with tab2:
                 avg_emission_wavelength = [(header['TITLE'], calculate_avg_emission_wavelength(df)) for header, df, extended_info in data_headers_and_dfs]
                 avg_emission_df = pd.DataFrame(avg_emission_wavelength, columns=["Title", "Average Emission Wavelength"])
         
                 st.dataframe(avg_emission_df, use_container_width=True)
                 avg_emission_csv = avg_emission_df.to_csv(index=False).encode('utf-8')
                 st.download_button(
                     label="Download average emission wavelengths as CSV",
                     data=avg_emission_csv,
                     file_name='avg_emission.csv',
                     mime='text/csv',
                 )
         
                 # Calculate min and max values with some padding
                 y_min = avg_emission_df['Average Emission Wavelength'].min() * 0.975
                 y_max = avg_emission_df['Average Emission Wavelength'].max() * 1.025
         
                 fig = go.Figure(data=[
                     go.Bar(
                         name='Average Emission Wavelength',
                         x=avg_emission_df['Title'],
                         y=avg_emission_df['Average Emission Wavelength'],
                         hovertemplate=
                         '<b>Title:</b> %{x}<br>' +
                         '<b>Average Emission Wavelength:</b> %{y}<extra></extra>',
                     )
                 ])
         
                 fig.update_layout(
                     width=width,
                     height=height,
                     template=template,
                     xaxis_title="Experiment",
                     yaxis_title="Average Emission Wavelength",
                     legend_title="Measurement",
                     yaxis_range=[y_min, y_max]  # Use calculated min and max values
                 )
         
                 st.plotly_chart(fig, use_container_width=True, theme=None, **{"config": config})
         
            with tab3:
                 integrals = [(header['TITLE'], calculate_integral(df)) for header, df, extended_info in data_headers_and_dfs]
                 integrals_df = pd.DataFrame(integrals, columns=["Title", "Integral"])
         
                 st.dataframe(integrals_df, use_container_width=True)
                 integrals_csv = integrals_df.to_csv(index=False).encode('utf-8')
                 st.download_button(
                     label="Download integrals as CSV",
                     data=integrals_csv,
                     file_name='integrals.csv',
                     mime='text/csv',
                 )
         
                 fig = go.Figure(data=[
                     go.Bar(
                         name='Integral',
                         x=integrals_df['Title'],
                         y=integrals_df['Integral'],
                         hovertemplate=
                         '<b>Title:</b> %{x}<br>' +
                         '<b>Integral:</b> %{y}<extra></extra>',
                     )
                 ])
         
                 fig.update_layout(
                     width=width,
                     height=height,
                     template=template,
                     xaxis_title="Experiment",
                     yaxis_title="Integral",
                     legend_title="Measurement",
                 )
         
                 st.plotly_chart(fig, use_container_width=True, theme=None, **{"config": config})


            with tab4:
                data_headers_and_dfs_normalized = [(header, normalize(df), extended_info) for header, df, extended_info
                                                   in data_headers_and_dfs]
                plot_data(data_headers_and_dfs_normalized)
                download_data(data_headers_and_dfs_normalized, suffix='_normalized')


if __name__ == "__main__":
    main()
