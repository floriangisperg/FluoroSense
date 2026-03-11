# FluoroSense

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://tuwien-jasco.streamlit.app/)
![Python](https://img.shields.io/badge/Python-3.8%20|%203.9%20|%203.10%20|%203.11-blue)
![Status](https://img.shields.io/badge/status-active-success)

A Streamlit-based web application for analyzing fluorescence spectroscopy data from Jasco spectrofluorometer instruments. Designed for protein kinetics research, specifically monitoring protein folding and unfolding through intrinsic tryptophan and tyrosine fluorescence.

**[Live Demo](https://tuwien-jasco.streamlit.app/)**

---

## Features

### Individual Spectra Analysis
- Interactive spectrum visualization
- Blank subtraction and baseline correction
- Average Emission Wavelength (AEW) calculation
- Spectral integral computation
- Normalized spectrum comparison
- Multiple export formats (CSV, SVG)

### Time Series Analysis
- Batch processing of multiple experimental conditions
- Real-time AEW tracking across timepoints
- Kinetic fitting with exponential decay models
- Spectral phase portraits
- Excel export with all processed data

### User Interface
- Modern dark theme optimized for scientific visualization
- Responsive layout with interactive Plotly charts
- Intuitive file upload and data management

---

## Scientific Background

FluoroSense leverages **intrinsic fluorescence** from tryptophan and tyrosine residues to monitor protein conformational changes:

| Protein State | Environment | Emission |
|---------------|-------------|----------|
| **Native** | Hydrophobic core (buried) | Blue-shifted (~330 nm) |
| **Denatured** | Solvent-exposed | Red-shifted (~350 nm) |

The **Average Emission Wavelength (AEW)** provides a robust, intensity-independent metric for tracking spectral shifts:

$$\text{AEW} = \frac{\sum_{i}^{j} \text{Intensity}_i \times \text{Wavelength}_i}{\sum_{i}^{j} \text{Intensity}_i}$$

---

## Installation

### Using uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/floriangisperg/fluorosense.git
cd fluorosense

# Install dependencies
uv sync

# Run the application
uv run streamlit run Main_Page.py
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/floriangisperg/fluorosense.git
cd fluorosense

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run Main_Page.py
```

---

## Usage

1. **Individual Spectra**: Navigate to the Individual Spectra page to analyze single emission spectra
   - Upload Jasco CSV files (exported from instrument software)
   - Optionally upload a blank for subtraction
   - View raw spectra, AEW, integrals, and normalized data

2. **Time Series**: Navigate to Time Series Analysis for kinetic experiments
   - Upload multiple files representing different timepoints
   - Configure blank subtraction per condition
   - Generate kinetic fits and export results

---

## Data Format

FluoroSense expects Jasco spectrofluorometer CSV files with the standard format:

```
TITLE,Sample Name,
...header fields...
XYDATA
Wavelength,Intensity
300,150.5
301,152.3
...
##### Extended Information
...metadata...
```

---

## Screenshots

<!-- Add your screenshots here -->
<!--
![Main Page](assets/screenshot_main.png)
![Individual Spectra](assets/screenshot_spectra.png)
![Time Series](assets/screenshot_timeseries.png)
-->

---

## Citation

If you use FluoroSense in your research, please cite:

```bibtex
@software{fluorosense2024,
  author = {Gisperg, Florian},
  title = {FluoroSense: A Streamlit Application for Fluorescence Spectroscopy Analysis},
  year = {2024},
  publisher = {GitHub},
  url = {https://github.com/floriangisperg/fluorosense}
}
```

---

## Author

**Florian Gisperg**
- IBD Group, TU Wien
- [GitHub](https://github.com/floriangisperg)

---

## Acknowledgments

Developed for protein kinetics research at the [Integrated Bioprocess Development (IBD Group)](https://www.tuwien.at/tch/icebe/ibdgroup), Research Area Biochemical Engineering, Institute of Chemical, Environmental and Bioscience Engineering, TU Wien.
