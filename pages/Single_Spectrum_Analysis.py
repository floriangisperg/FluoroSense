from pages.Refolding_Analysis import upload_jasco_rawdata
from pages.Refolding_Analysis import calculate_avg_emission_wavelength
import streamlit as st
import plotly.graph_objects as go
import numpy as np
from sklearn.preprocessing import MinMaxScaler
import pandas as pd

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

# Your existing dataframe to .txt file conversion function
def single_measurement_df_to_txt(df, header, suffix=''):
    csv = df.to_csv(sep='\t', index=False).encode('utf-8')
    return csv

def file_uploader():
    uploaded_files = st.sidebar.file_uploader("Choose CSV files", accept_multiple_files=True)
    data_headers_and_dfs = [upload_jasco_rawdata(file) for file in uploaded_files]
    return data_headers_and_dfs

@st.cache_data
def convert_df_to_txt(df, header):
    txt = single_measurement_df_to_txt(df, header)
    return txt.encode('utf-8')  # Encode as byte stream for download


def download_data(data_headers_and_dfs, suffix=''):
    for header, df, extended_info in data_headers_and_dfs:
        csv = single_measurement_df_to_txt(df, header, suffix)
        st.download_button(
            label=f"Download {header['TITLE']}{suffix} as .txt",
            data=csv,
            file_name=f"{header['TITLE']}{suffix}.txt",
            mime='text/plain',
        )

def normalize(df):
    scaler = MinMaxScaler()
    df_normalized = pd.DataFrame(scaler.fit_transform(df), columns=df.columns, index=df.index)
    return df_normalized

def plot_data(data_headers_and_dfs, template=template, width=width, height=height, config=config):
    fig = go.Figure()

    for i, (header, df, extended_info) in enumerate(data_headers_and_dfs):
        fig.add_trace(
            go.Scatter(
                x=df.index,
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
        legend_title="Title"
    )

    st.plotly_chart(fig, use_container_width=True, theme=None, **{"config": config})


def main():
    data_headers_and_dfs = file_uploader()

    if data_headers_and_dfs:
        # Check for duplicate headers
        titles = [header['TITLE'] for header, df, extended_info in data_headers_and_dfs]
        if len(titles) != len(set(titles)):
            st.warning("Duplicate files detected. Please upload only unique files.")
        else:
            tab1, tab2, tab3 = st.tabs(["Data Visualization", "Average Emission Wavelength", "Normalized Data"])

            with tab1:
                #st.write("Dataframes loaded successfully. Ready for visualization.")
                plot_data(data_headers_and_dfs)
                #st.write("Visualization complete. Ready for download.")
                download_data(data_headers_and_dfs)

            with tab2:
                avg_emission_wavelength = [(header['TITLE'], calculate_avg_emission_wavelength(df)[1]) for
                                           header, df, extended_info in data_headers_and_dfs]
                avg_emission_df = pd.DataFrame(avg_emission_wavelength,
                                               columns=["Title", "Average Emission Wavelength"])

                st.dataframe(avg_emission_df)
                avg_emission_csv = avg_emission_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download average emission wavelengths as CSV",
                    data=avg_emission_csv,
                    file_name='avg_emission.csv',
                    mime='text/csv',
                )

            with tab3:
                data_headers_and_dfs_normalized = [(header, normalize(df), extended_info) for header, df, extended_info
                                                   in data_headers_and_dfs]
                plot_data(data_headers_and_dfs_normalized)
                download_data(data_headers_and_dfs_normalized, suffix='_normalized')


if __name__ == "__main__":
    main()