# FluoroSense

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://fluorosense.streamlit.app/)
![Python](https://img.shields.io/badge/Python-3.11%20|%203.12%20|%203.13-blue)
![Status](https://img.shields.io/badge/status-active-success)

A Streamlit-based web application for analyzing fluorescence spectroscopy data from Jasco spectrofluorometer instruments. Designed for protein kinetics research, specifically monitoring protein folding and unfolding through intrinsic tryptophan and tyrosine fluorescence.

**[Live Demo](https://fluorosense.streamlit.app/)**

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
git clone https://github.com/floriangisperg/FluoroSense.git
cd FluoroSense

# Install dependencies
uv sync

# Run the application
uv run streamlit run Home.py
```

> `requirements.txt` is auto-generated from `pyproject.toml` (via `uv export`) and is what the Streamlit Cloud deployment installs — regenerate it after dependency changes rather than editing it by hand.

### Using pip

```bash
# Clone the repository
git clone https://github.com/floriangisperg/FluoroSense.git
cd FluoroSense

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run Home.py
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

FluoroSense understands three input formats:

**1. Jasco single-spectrum export** — header fields, an `XYDATA` section of `wavelength,intensity` rows (no column header), and an `##### Extended Information` footer:

```
TITLE,Sample Name,
...header fields...
XYDATA
300.0000,46.0996
301.0000,152.3
...
##### Extended Information
...metadata...
```

**2. Jasco multi-column time-series export** — same wrapper, but `XYDATA` begins with a header row of process times (minutes) and one intensity column per timepoint:

```
XYDATA
,0,2.56667,5.15,...
300.0000,448.33,451.2,449.9,...
300.5000,452.10,455.0,453.7,...
...
##### Extended Information
```

**3. FluoroSense exports** — files previously processed and downloaded from FluoroSense itself (`.txt`, `.csv`, `.xlsx`) can be re-uploaded to either module.

Incomplete/ragged wavelength rows are dropped with a visible warning so all spectra share one wavelength grid.

---

## Screenshots

<!-- Add your screenshots here -->
<!--
![Main Page](assets/screenshot_main.png)
![Individual Spectra](assets/screenshot_spectra.png)
![Time Series](assets/screenshot_timeseries.png)
-->

---

## Development & Testing

```bash
uv sync                          # includes the dev group (pytest)
uv run python -m pytest tests/ -q
```

---

## Citation

If you use FluoroSense in your research, please cite:

```bibtex
@software{fluorosense2024,
  author = {Gisperg, Florian},
  title = {FluoroSense: A Streamlit Application for Fluorescence Spectroscopy Analysis},
  year = {2024},
  publisher = {GitHub},
  url = {https://github.com/floriangisperg/FluoroSense}
}
```

---

## License

FluoroSense is released into the public domain under the [Unlicense](LICENSE).

---

## Author

**Florian Gisperg**
- IBD Group, TU Wien
- [GitHub](https://github.com/floriangisperg)

---

## Acknowledgments

Developed for protein kinetics research at the [Integrated Bioprocess Development (IBD Group)](https://www.tuwien.at/tch/icebe/ibdgroup), Research Area Biochemical Engineering, Institute of Chemical, Environmental and Bioscience Engineering, TU Wien.
