import streamlit as st
st.header("Jasco Fluorimeter Data Analysis")
st.markdown("""
This application is designed to analyze the .csv output files from Jasco Spectrofluorometer. It is structured into two modules:

1. **Time Series Measurement Analysis/Refolding Analysis**
2. **Single Spectrum Analysis**

## Measurement Principles

### Fluorescence emission spectra of intrinsic tryptophan and tyrosine as a monitoring tool for refolding of inclusion bodies

The fluorescence spectra originate from tryptophan and tyrosine residues in the sequence of the protein of interest. The monitoring is based on the sensitivity of tryptophan and tyrosine residues to hydrophobicity/polarity of their local environment.

- In the native (folded) protein, the hydrophobic tryptophan and tyrosine side chains are buried in the protein core.
- In the denatured (unfolded) protein, these residues are more exposed to the solvent, i.e., in a less hydrophobic local environment.

Therefore, the denaturation of the protein is accompanied by the red-shift (toward higher wavelength) of a tryptophan and tyrosine fluorescence peak maxima as those residues become more solvent exposed. The refolding of the protein of interest, which is essentially the inverse process (from denatured to native state), is then characterized by the shift of the fluorescence maximum in the opposite direction.

The shift in the maxima of fluorescence peaks is most efficiently characterized by calculating the centre of mass of the peak, here called **Average Emission Wavelength (AEW)**, of each spectrum in the time series.

""")

st.latex(r'''
    AEW = \frac{\sum_{i}^{j} \text{Int}_i \times \text{Wavel}_i}{\sum_{i}^{j} \text{Int}_i}
''')

st.markdown("""

## Use Cases

### Time Series Measurement

This module is used to analyze time series measurements where data are collected in distinct time intervals over multiple minutes/hours.

### Individual Spectra

This module is designed to visualize and process the individual spectra from a .csv output files.

""")
