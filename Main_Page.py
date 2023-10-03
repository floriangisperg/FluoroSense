import streamlit as st
st.set_page_config(layout="wide")

st.title('FluoroSense')

st.markdown('This application is designed to analyze the .csv output files from Jasco Spectrofluorometer. It is structured into two modules – Time Series Measurement Analysis/Refolding Analysis and Single Spectrum Analysis.')

st.header('Measurement Principles')
st.markdown('Fluorescence emission spectra of intrinsic tryptophan and tyrosine as a monitoring tool for refolding of inclusion bodies')

st.markdown('---')  # Divider line

st.markdown('The fluorescence spectra originate from tryptophan and tyrosine residues in the sequence of the protein of interest. The monitoring is based on the sensitivity of tryptophan and tyrosine residues to hydrophobicity/polarity of their local environment. In the native (folded) protein the hydrophobic tryptophan and tyrosine side chains are buried in the protein core whereas in the denatured (unfolded) protein these residues are more exposed to the solvent, i.e. in less hydrophobic local environment. Therefore, the denaturation of the protein is accompanied with the red-shift (toward higher wavelength) of a tryptophan and tyrosine fluorescence peak maxima as those residues become more solvent exposed. The refolding of the protein of interest, which is essentially the inverse process (from denatured to native state), is then characterized by the shift of the fluorescence maximum in the opposite direction.')
st.markdown('The shift in the maxima of a fluorescence peaks is most efficiently characterized by calculating the centre of a mass of the peak, here called average emission wavelength (AEW), of each spectrum in the time series.')

st.latex(r'\text{AEW} = \frac{\sum_{i}^{j} \text{Int}_i \times \text{Wavel}_i}{\sum_{i}^{j} \text{Int}_i}')

st.header('Use Cases')
st.markdown('---')  # Divider line
st.subheader('Time Series Measurement')
st.markdown('This module is used to analyze time series measurements where data are collected in the distinct time intervals over multiple minutes/hours.')
st.subheader('Individual Spectra')
st.markdown('This module is designed to visualize and process the individual spectra from a .csv output files.')
st.markdown('Text written by Eva Prada')
st.markdown('---')  # Divider line

c1, c2, c3 = st.columns(3)

with c1:
    st.info('**[@IBD Group](https://www.tuwien.at/tch/icebe/ibdgroup)**', icon="🎓")

with c2:
    st.info('**[CD Lab for Inclusion Body Processing 4.0](https://www.tuwien.at/tch/icebe/ibdgroup/forschungsthemen-projekte/inclusion-body-processing-40)**', icon="🧬")

with c3:
    st.info('**[@floriangisperg](https://github.com/floriangisperg)**', icon="👨‍💻")
