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
                                    'v1hovermode'
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
    header = {}
    xydata = []
    extended_info = {}

    lines = uploaded_file.readlines()
    mode = 'header'
    for line in lines:
        line = line.decode().strip() # decode byte stream to string
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
         
def calculate_integrals(df):
    return df.apply(lambda col: np.trapz(col, dx=1), axis=0)
def calculate_avg_emission_wavelength(df):
    avg_emission_wavelength = []
    for col in df.columns:
        weighted_sum = np.sum(df.index * df[col])
        total_intensity = np.sum(df[col])
        avg_emission_wavelength.append(weighted_sum / total_intensity)
    return avg_emission_wavelength
         
def calculate_max_emission_wavelength(df):
    max_emission_wavelength = []
    for col in df.columns:
        max_wavelength = df.index[np.argmax(df[col])]
        max_emission_wavelength.append(max_wavelength)
    return max_emission_wavelength

def augment_dataframe(df, avg_emission_wavelength, integrals):
    df_transposed = df.transpose()
    df_transposed_aew = df_transposed.copy()
    df_transposed_aew["Average emission wavelength [nm]"] = avg_emission_wavelength
    df_transposed_aew_integral = df_transposed_aew.copy()
    df_transposed_aew_integral["Integral"] = integrals
    df_transposed_aew_integral.reset_index(inplace = True)
    df_transposed_aew_integral.rename(columns={df_transposed_aew_integral.columns[0]: "Process Time [min]"}, inplace=True)
    df_transposed_aew_integral["Process Time [min]"] = pd.to_numeric(df_transposed_aew_integral["Process Time [min]"], errors='coerce')
    df_transposed_aew_integral["Process Time [h]"] = round(df_transposed_aew_integral["Process Time [min]"] / 60, 3)
    return df_transposed, df_transposed_aew_integral 


@st.cache_data
def plot_data(df, y_column, template=template, width=width, height=height, config=config):
    """

    :rtype: object
    """
    fig = px.scatter(df, x="Process Time [h]", y=y_column, template=template)
    fig.update_layout(autosize=False, width=width, height=height)
    # fig.show(config=config)
    return fig
@st.cache_data
def plot_intensity(df, interval=None, template=template, width=width, height=height, config=config):
    if interval is not None:
        reduced_range = np.arange(0, df["Process Time [h]"].max(), interval)
        reduced_range = np.append(reduced_range, df["Process Time [h]"].max())
        df = df[df["Process Time [h]"].isin(reduced_range)]
        df = df.reset_index(drop=True)

    df_plot = df.T
    df_plot.columns = df_plot.iloc[-1]
    df_plot = df_plot[:-4]

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

    # fig.show(config=config)
    return fig
@st.cache_data
def plot_contour(df, ncontours=15, template=template, width=width, height=height, config=config):
    Z = df.to_numpy()
    X = np.array(df.columns, dtype=float)
    Y = np.array(df.index, dtype=float)

    fig = go.Figure(data =
        go.Contour(
            z=Z,
            x=X,
            y=Y,
            colorscale='Viridis',
            hovertemplate='Wavelength [nm]: %{x}<br>Time: %{y}<br>Intensity: %{z}<extra></extra>',
            ncontours=ncontours,
            colorbar=dict(title="Intensity")  # here is how to add the color bar title
        ))

    fig.update_layout(
        xaxis_title='Wavelength [nm]',
        yaxis_title='Time',
        autosize=False,
        width=width,
        height=height,
    )

    #fig.show(config=config)
    return fig
@st.cache_data
def save_to_excel(header, df, engine='xlsxwriter'):
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


@st.cache_data
def df_to_txt(df, y_column):
    df_subset = df[["Process Time [h]", y_column]]
    str_io = StringIO()
    df_subset.to_csv(str_io, sep='\t', index=False)
    return str_io.getvalue()

st.title("Jasco Refolding Monitoring App")
with st.expander("Upload file here"):
    uploaded_file = st.sidebar.file_uploader("Choose a file")

if uploaded_file:
    header, df, extended_info = upload_jasco_rawdata(uploaded_file)
    # use header, df, and extended_info here. For example:
    # st.write(header)
    # st.dataframe(df)
    # if extended_info is not None:
    #     st.write(extended_info)

    integrals = calculate_integrals(df)
    avg_emission_wavelength = calculate_avg_emission_wavelength(df)
    df_transposed, df_augmented = augment_dataframe(df, avg_emission_wavelength, integrals)
    max_emission_wavelength = calculate_max_emission_wavelength(df)
    df_augmented["Max emission wavelength [nm]"] = max_emission_wavelength


    # download buttons
    excel_data = save_to_excel(header, df_augmented)
    st.sidebar.download_button(
    label="Download processed Data as Excel-File",
    data=excel_data,
    file_name=header["TITLE"] + "_processed" + ".xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
         
    aew_df_txt = df_to_txt(df_augmented, "Average emission wavelength [nm]")
    st.sidebar.download_button(
        label="AEW as .txt",
        data= aew_df_txt,
        file_name= header["TITLE"] + "_aew" + ".txt",
        mime='text/csv',
    )
    intensity_df_txt = df_to_txt(df_augmented, "Integral")
    st.sidebar.download_button(
        label="Intensity as .txt",
        data=intensity_df_txt,
        file_name=header["TITLE"] + "_intensity" + ".txt",
        mime='text/csv',
    )
    max_wavelength_df_txt = df_to_txt(df_augmented, "Max emission wavelength [nm]")
    st.sidebar.download_button(
         label="Max Wavelength as .txt",
         data=max_wavelength_df_txt,
         file_name=header["TITLE"] + "_max_wavelength" + ".txt",
         mime='text/csv',
    )

    # # Convert the dictionary to a Pandas DataFrame
    # # Create the sidebar with the DataFrame
    if header:
        # df_info = pd.DataFrame.from_dict(header, orient='index', columns=['Value'])
        # st.sidebar.table(df_info)
        st.sidebar.write("---")
        for key, value in header.items():
            st.sidebar.text(f"{key}: {value}")


    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Experiment all","Average Emission Wavelength", "Max Emission Wavelength", "Integral of Intensities", "Contour"])

    with tab1:
        # Add a slider to the sidebar:
        interval = st.select_slider(
            'Select time interval of plotted graphs',
            options=[None, 0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2], value = 0.25)
        # Use the interval value from the slider in your function
        fig = plot_intensity(df_augmented, interval=interval)
        # Show the plot
        st.plotly_chart(fig, use_container_width=True, theme=None, **{"config": config})

        # if fig:
        #     buffer = io.StringIO()
        #     fig.write_html(buffer, include_plotlyjs='cdn')
        #     html_bytes = buffer.getvalue().encode()
        #
        #     st.download_button(
        #         label='Download HTML',
        #         data=html_bytes,
        #         file_name='stuff.html',
        #         mime='text/html'
        #     )
    with tab2:
       st.header("Average emission wavelength [nm]")
       fig = plot_data(df_augmented, "Average emission wavelength [nm]")
       st.plotly_chart(fig, use_container_width=True, theme = None, **{"config": config})

    with tab3:
       st.header("Max Emission Wavelength [nm]")
       fig = plot_data(df_augmented, "Max emission wavelength [nm]")
       st.plotly_chart(fig, use_container_width=True, theme=None, **{"config": config})

    with tab4:
       st.header("Integral of the intensity")
       fig = plot_data(df_augmented, "Integral")
       st.plotly_chart(fig, use_container_width=True, theme = None, **{"config": config})

    with tab5:
       st.header("Contour plot")
       fig = plot_contour(df_transposed) #ncontours=15)
       st.plotly_chart(fig, use_container_width=True, theme=None, **{"config": config})

