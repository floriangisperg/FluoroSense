# CLAUDE.md

Guidance for AI coding agents working in this repository.

## Project Overview

FluoroSense is a Streamlit web application for analyzing fluorescence spectroscopy data from Jasco spectrofluorometer instruments (Jasco FP-8550). It processes emission spectra for protein kinetics research — monitoring protein folding/unfolding through intrinsic tryptophan and tyrosine fluorescence.

Live deployment: https://fluorosense.streamlit.app/ (Streamlit Community Cloud, deploys from `main` using `requirements.txt`).

## Running the Application

```bash
uv sync
uv run streamlit run Home.py
```

Python `>=3.11,<3.14` (developed on 3.13).

## Dependencies (uv-managed)

- `pyproject.toml` is the single source of truth; `uv.lock` pins the full resolution and is committed.
- Local setup: `uv sync` creates `.venv` (including the `dev` dependency group with pytest), then `uv run ...` for everything.
- `requirements.txt` is **generated, not hand-written**. Streamlit Community Cloud installs from it, so regenerate it after any dependency change:
  `uv export --format requirements-txt --no-hashes --no-dev --no-emit-project > requirements.txt`
- Key direct dependencies: streamlit==1.57.0, plotly==5.15.0, numpy==2.3.5, pandas==2.3.3, scikit-learn==1.8.0 (only for MinMaxScaler normalization), openpyxl==3.1.2 (Excel export/import), scipy==1.17.1 (integration + curve fitting).

## Tests

```bash
uv run python -m pytest tests/ -q
```

A synthetic regression fixture (`tests/fixtures/synthetic_timeseries.csv`) is committed; the parser tests skip loudly if it goes missing. No real experiment data is ever committed. The parser imports as a plain package (`fluorosense`), no install step needed when running pytest from the repo root.

## Architecture

Entry point is `Home.py` (landing page). Streamlit's multi-page convention: files in `pages/` named with emoji-number prefixes become the sidebar navigation.

### pages/

- **pages/1_🔬_Individual_Spectra.py** (~390 lines): upload one or more spectra, optional blank subtraction, optional spectral-range limiting, per-file metrics (AEW, max emission wavelength, integral), normalized-spectrum comparison (MinMaxScaler), TXT/CSV downloads.
- **pages/2_⏳_Time_Series_Measurement.py** (~1650 lines, the big one): Single File and Batch Processing modes. Batch runs are `TimeSeriesRun` dataclass instances kept in `st.session_state['batch_runs']`. Features: per-run blank subtraction (single timepoint or averaged range), shared spectral-range limiting, per-timepoint metrics, exponential kinetic fits (decay/rise via `scipy.optimize.curve_fit` with 95% CIs, t½, R²), spectral phase portraits (width vs AEW), contour plots, Excel export and tidy CSV export with provenance header.

### fluorosense/ package — the actual logic, pages are thin UI wrappers

- **io.py**: `parse_jasco_rawdata()` parses Jasco text exports (header key/value lines → `XYDATA` section → `##### Extended Information` footer). Handles both headerless single spectra (`"300.0000,46.0996"` first row) and multi-column time-series exports (first XYDATA row is a header like `",0,1.7333,..."` of process-time-minutes columns). Drops ragged/incomplete rows with a warning so all spectra share one wavelength grid. `parse_spectral_file()` additionally accepts FluoroSense's own re-exports (.txt/.csv/.xlsx). `as_individual_spectrum()` normalizes to `Wavelength [nm]`/`Intensity` columns.
- **metrics.py**: AEW, spectral integral (scipy `simpson`), max emission wavelength, spectral width (intensity-weighted std dev), range filters, and `augment_dataframe()` which builds the per-timepoint metrics table with `Process Time [min]/[h]` columns.

### styles.py

Dark Lab theme: injects CSS (`apply_dark_lab_theme()`), exposes `get_plotly_dark_template()` and `EMISSION_PALETTE`. Every page calls `apply_dark_lab_theme()` right after `st.set_page_config()`.

### Shared plot configuration

Both pages: plots 1200×600, SVG download export (1200×600), custom modebar draw tools. Template comes from `styles.get_plotly_dark_template()`.

## Data Formats

1. **Jasco single-spectrum CSV**: header key/value lines (`TITLE,...`, `FIRSTX/LASTX/NPOINTS`), then `XYDATA` with `wavelength,intensity` rows (no column header), then `##### Extended Information`.
2. **Jasco multi-column time-series CSV**: same wrapper; `XYDATA` first row is a comma-prefixed header of process times in minutes (`,0,2.56667,...`), one intensity column per timepoint, wavelengths as row index (300–450 nm, 0.5 nm steps).
3. **FluoroSense exports** (its own .txt/.xlsx/.csv outputs) are re-importable by both pages.

Sample instrument files in `data/timeseries/Exp1.csv` … `Exp9.csv` (untracked, gitignored — real experiment data never enters git).

## Conventions and Gotchas

- Parsed dataframes carry parser warnings in `df.attrs["parse_warnings"]`; read with `fluorosense.io.parse_warnings(df)`. DataFrame transformations must copy attrs along (see `_copy_attrs` helpers) or warnings are lost.
- Wavelength columns in augmented tables are stringified floats (`"300.0"`); metric columns are excluded from spectra via `TIME_SERIES_METADATA_COLUMNS` in `fluorosense.metrics`.
- `upload_jasco_rawdata` is `@st.cache_data`-wrapped in page 2 (Streamlit file objects as cache keys).
- Kinetic-fit acceptance heuristics (in `fit_kinetic_data`): fits are rejected when amplitude Δy < 0.5 nm, R² < 0.5, or t½ < 60 s. These thresholds are scientific choices — document any change.
- The local `.venv` in the working copy may be stale; the de-facto dev environment is system Python 3.13. Recreate with `pip install -r requirements.txt` if needed.
- After changing parsing/metrics behavior, extend or update `tests/` and, when needed, the fixture files.
