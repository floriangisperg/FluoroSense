"""Spectral preprocessing and derived fluorescence metrics."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.integrate import simpson


AEW_COLUMN = "Average emission wavelength [nm]"
INTEGRAL_COLUMN = "Integral"
MAX_WAVELENGTH_COLUMN = "Max emission wavelength [nm]"
SPECTRAL_WIDTH_COLUMN = "Spectral width [nm]"
TIME_SERIES_METADATA_COLUMNS = {
    "Process Time [min]",
    "Process Time [h]",
    AEW_COLUMN,
    INTEGRAL_COLUMN,
    MAX_WAVELENGTH_COLUMN,
    SPECTRAL_WIDTH_COLUMN,
}


def time_series_wavelength_columns(df: pd.DataFrame) -> list[object]:
    """Return columns that represent wavelength spectra in an augmented time-series table."""

    wavelength_columns = []
    for column in df.columns:
        if column in TIME_SERIES_METADATA_COLUMNS:
            continue
        try:
            wavelength = float(str(column).strip())
        except (TypeError, ValueError):
            continue
        if np.isfinite(wavelength):
            wavelength_columns.append(column)
    return wavelength_columns


def _copy_attrs(source: pd.DataFrame, target: pd.DataFrame) -> pd.DataFrame:
    target.attrs.update(source.attrs)
    return target


def coerce_time_series_data(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Return numeric time-series spectra indexed by wavelength."""

    if df.empty:
        return df.copy(), []

    warnings: list[str] = []
    numeric_df = df.select_dtypes(include=["number"]).copy()
    if numeric_df.empty:
        numeric_df = df.apply(pd.to_numeric, errors="coerce").select_dtypes(include=["number"])

    numeric_df.index = pd.to_numeric(numeric_df.index, errors="coerce")
    numeric_df = numeric_df[~pd.isna(numeric_df.index)]
    numeric_df = numeric_df.dropna(how="all").dropna(axis=1, how="all")

    incomplete_rows = int(numeric_df.isna().any(axis=1).sum())
    if incomplete_rows:
        numeric_df = numeric_df.dropna(axis=0, how="any")
        warnings.append(
            f"{incomplete_rows} incomplete wavelength row(s) dropped for a consistent spectral range."
        )

    numeric_df = numeric_df.sort_index()
    return _copy_attrs(df, numeric_df), warnings


def filter_spectral_range(
    df: pd.DataFrame,
    wavelength_min: float | None = None,
    wavelength_max: float | None = None,
) -> pd.DataFrame:
    """Filter spectra to an inclusive wavelength range."""

    if df.empty or (wavelength_min is None and wavelength_max is None):
        return df.copy()

    numeric_df = df.copy()
    numeric_df.index = pd.to_numeric(numeric_df.index, errors="coerce")
    mask = ~pd.isna(numeric_df.index)
    if wavelength_min is not None:
        mask &= numeric_df.index >= wavelength_min
    if wavelength_max is not None:
        mask &= numeric_df.index <= wavelength_max
    return _copy_attrs(df, numeric_df.loc[mask].copy())


def filter_single_spectrum_range(
    df: pd.DataFrame,
    wavelength_min: float | None = None,
    wavelength_max: float | None = None,
) -> pd.DataFrame:
    """Filter an individual spectrum dataframe to an inclusive wavelength range."""

    if df.empty or (wavelength_min is None and wavelength_max is None):
        return df.copy()

    filtered = df.copy()
    wavelengths = pd.to_numeric(filtered["Wavelength [nm]"], errors="coerce")
    mask = ~pd.isna(wavelengths)
    if wavelength_min is not None:
        mask &= wavelengths >= wavelength_min
    if wavelength_max is not None:
        mask &= wavelengths <= wavelength_max
    return _copy_attrs(df, filtered.loc[mask].copy())


def spectral_range(df: pd.DataFrame) -> tuple[float | None, float | None, int]:
    """Return min wavelength, max wavelength, and point count."""

    if df.empty:
        return None, None, 0
    wavelengths = pd.to_numeric(df.index, errors="coerce")
    wavelengths = wavelengths[~pd.isna(wavelengths)]
    if len(wavelengths) == 0:
        return None, None, 0
    return float(np.min(wavelengths)), float(np.max(wavelengths)), int(len(wavelengths))


def calculate_integrals(df: pd.DataFrame) -> pd.Series:
    """Calculate spectral integrals for each timepoint."""

    numeric_df, _ = coerce_time_series_data(df)
    if numeric_df.empty:
        return pd.Series(dtype=float)

    def integrate_column(col: pd.Series) -> float:
        valid = col.dropna()
        if len(valid) < 2:
            return np.nan
        return float(simpson(valid.to_numpy(dtype=float), x=valid.index.to_numpy(dtype=float)))

    return numeric_df.apply(integrate_column, axis=0)


def calculate_avg_emission_wavelength(df: pd.DataFrame) -> list[float]:
    """Calculate average emission wavelength for each timepoint."""

    numeric_df, _ = coerce_time_series_data(df)
    if numeric_df.empty:
        return []

    values: list[float] = []
    for col in numeric_df.columns:
        valid = numeric_df[col].dropna()
        if valid.empty or (valid <= 0).all():
            values.append(np.nan)
            continue
        wavelengths = valid.index.to_numpy(dtype=float)
        intensities = valid.to_numpy(dtype=float)
        total_intensity = np.sum(intensities)
        values.append(float(np.sum(wavelengths * intensities) / total_intensity) if total_intensity > 0 else np.nan)
    return values


def calculate_max_emission_wavelength(df: pd.DataFrame) -> list[float]:
    """Find max emission wavelength for each timepoint."""

    numeric_df, _ = coerce_time_series_data(df)
    if numeric_df.empty:
        return []

    values: list[float] = []
    for col in numeric_df.columns:
        valid = numeric_df[col].dropna()
        if valid.empty:
            values.append(np.nan)
        else:
            values.append(float(valid.index[np.argmax(valid.to_numpy(dtype=float))]))
    return values


def calculate_spectral_width(df: pd.DataFrame, avg_emission_wavelength: list[float]) -> list[float]:
    """Calculate weighted spectral width for each timepoint."""

    numeric_df, _ = coerce_time_series_data(df)
    if numeric_df.empty:
        return []

    widths: list[float] = []
    for i, col in enumerate(numeric_df.columns):
        valid = numeric_df[col].dropna()
        aew = avg_emission_wavelength[i] if i < len(avg_emission_wavelength) else np.nan
        if valid.empty or np.isnan(aew):
            widths.append(np.nan)
            continue
        wavelengths = valid.index.to_numpy(dtype=float)
        spectrum = valid.to_numpy(dtype=float)
        total_intensity = np.sum(spectrum)
        if total_intensity <= 0:
            widths.append(np.nan)
            continue
        weighted_var = np.sum(spectrum * (wavelengths - aew) ** 2) / total_intensity
        widths.append(float(np.sqrt(weighted_var)))
    return widths


def calculate_single_spectrum_aew(df: pd.DataFrame) -> float:
    """Calculate AEW for a single spectrum dataframe."""

    valid = df[["Wavelength [nm]", "Intensity"]].dropna()
    total_intensity = valid["Intensity"].sum()
    if total_intensity <= 0:
        return np.nan
    return float((valid["Wavelength [nm]"] * valid["Intensity"]).sum() / total_intensity)


def calculate_single_spectrum_integral(df: pd.DataFrame) -> float:
    """Calculate integral for a single spectrum dataframe."""

    valid = df[["Wavelength [nm]", "Intensity"]].dropna()
    if len(valid) < 2:
        return np.nan
    return float(simpson(valid["Intensity"].to_numpy(dtype=float), x=valid["Wavelength [nm]"].to_numpy(dtype=float)))


def augment_dataframe(
    df: pd.DataFrame,
    avg_emission_wavelength: list[float],
    integrals: pd.Series,
    max_emission_wavelength: list[float],
    spectral_width_values: list[float],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Combine raw spectra and derived metrics into display dataframes."""

    df_transposed = df.transpose()
    df_augmented = df_transposed.copy()
    df_augmented[AEW_COLUMN] = avg_emission_wavelength
    df_augmented[INTEGRAL_COLUMN] = integrals
    df_augmented[MAX_WAVELENGTH_COLUMN] = max_emission_wavelength
    df_augmented[SPECTRAL_WIDTH_COLUMN] = spectral_width_values
    df_augmented.reset_index(inplace=True)
    df_augmented.rename(columns={df_augmented.columns[0]: "Process Time [min]"}, inplace=True)

    process_time = pd.to_numeric(df_augmented["Process Time [min]"], errors="coerce")
    if process_time.isna().any():
        process_time = pd.Series(range(len(df_augmented)), index=df_augmented.index, dtype=float)
    df_augmented["Process Time [min]"] = process_time
    df_augmented["Process Time [h]"] = round(df_augmented["Process Time [min]"] / 60, 3)
    return df_transposed, df_augmented
