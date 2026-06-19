"""Jasco file parsing helpers."""

from __future__ import annotations

from io import BytesIO, StringIO
from dataclasses import dataclass, field
from typing import BinaryIO

import numpy as np
import pandas as pd


@dataclass
class JascoParseResult:
    """Parsed Jasco file payload."""

    header: dict[str, str]
    data: pd.DataFrame
    extended_info: dict[str, str]
    warnings: list[str] = field(default_factory=list)


METRIC_COLUMNS = {
    "Average emission wavelength [nm]",
    "Integral",
    "Max emission wavelength [nm]",
    "Spectral width [nm]",
    "Process Time [min]",
    "Process Time [h]",
}


def _read_bytes(source: bytes | BinaryIO) -> bytes:
    if isinstance(source, bytes):
        return source

    position = None
    if hasattr(source, "tell") and hasattr(source, "seek"):
        try:
            position = source.tell()
            source.seek(0)
        except (OSError, ValueError):
            position = None

    content = source.read()
    if position is not None:
        try:
            source.seek(position)
        except (OSError, ValueError):
            pass

    if isinstance(content, str):
        return content.encode("utf-8")
    return content


def _read_lines(source: bytes | BinaryIO) -> list[bytes]:
    if isinstance(source, bytes):
        return source.splitlines()
    return source.readlines()


def _decode_line(line: bytes, file_name: str | None) -> str:
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            return line.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    label = f"'{file_name}'" if file_name else "Uploaded file"
    raise ValueError(f"{label} is not a valid Jasco text file.")


def _header_float(header: dict[str, str], key: str) -> float | None:
    try:
        return float(str(header.get(key, "")).strip())
    except (TypeError, ValueError):
        return None


def _header_int(header: dict[str, str], key: str) -> int | None:
    value = _header_float(header, key)
    return int(value) if value is not None else None


def _attach_warnings(df: pd.DataFrame, warnings: list[str]) -> pd.DataFrame:
    if warnings:
        df.attrs["parse_warnings"] = warnings
    return df


def _copy_attrs(source: pd.DataFrame, target: pd.DataFrame) -> pd.DataFrame:
    target.attrs.update(source.attrs)
    return target


def _decode_text(content: bytes, file_name: str | None) -> str:
    return "\n".join(_decode_line(line, file_name) for line in content.splitlines())


def _numeric_column_name(column: object) -> float | None:
    try:
        value = float(str(column).strip())
    except (TypeError, ValueError):
        return None
    return value if np.isfinite(value) else None


def _row_is_all_numeric(row: list[str]) -> bool:
    """True when every field in a data row parses as a finite number.

    Distinguishes a headerless XYDATA section (whose first row is already data,
    e.g. ``"300.0000,46.0996"``) from one that begins with a column header such
    as ``",0,1.7333,..."`` (multi-column time-series) or ``"Wavelength,Intensity"``.
    """
    if not row:
        return False
    for field in row:
        try:
            value = float(str(field).strip())
        except (TypeError, ValueError):
            return False
        if not np.isfinite(value):
            return False
    return True


def _title_from_name(file_name: str | None, fallback: str = "FluoroSense export") -> str:
    if not file_name:
        return fallback
    return file_name.rsplit(".", 1)[0]


def _table_to_spectral_df(table: pd.DataFrame) -> pd.DataFrame:
    if table.empty:
        return pd.DataFrame()

    df = table.copy()
    df.columns = [str(col).strip() for col in df.columns]

    if "Wavelength [nm]" in df.columns:
        spectrum = df.copy()
        spectrum["Wavelength [nm]"] = pd.to_numeric(spectrum["Wavelength [nm]"], errors="coerce")
        spectrum = spectrum.dropna(subset=["Wavelength [nm]"])
        value_columns = [
            col
            for col in spectrum.columns
            if col != "Wavelength [nm]" and pd.to_numeric(spectrum[col], errors="coerce").notna().any()
        ]
        if not value_columns:
            return pd.DataFrame()
        result = spectrum[value_columns].apply(pd.to_numeric, errors="coerce")
        result.index = spectrum["Wavelength [nm]"].astype(float)
        result.index.name = ""
        return result.dropna(how="all").sort_index()

    time_column = None
    if "Process Time [min]" in df.columns:
        time_column = "Process Time [min]"
        process_time = pd.to_numeric(df[time_column], errors="coerce")
    elif "Process Time [h]" in df.columns:
        time_column = "Process Time [h]"
        process_time = pd.to_numeric(df[time_column], errors="coerce") * 60
    else:
        process_time = pd.Series(np.arange(len(df), dtype=float), index=df.index)

    wavelength_columns: list[str] = []
    wavelengths: list[float] = []
    for col in df.columns:
        if col == time_column or col in METRIC_COLUMNS:
            continue
        wavelength = _numeric_column_name(col)
        if wavelength is None:
            continue
        wavelength_columns.append(col)
        wavelengths.append(wavelength)

    if not wavelength_columns:
        return pd.DataFrame()

    spectral_rows = df[wavelength_columns].apply(pd.to_numeric, errors="coerce")
    spectral_rows = spectral_rows.loc[process_time.notna()]
    process_time = process_time.loc[spectral_rows.index]
    if spectral_rows.empty:
        return pd.DataFrame()

    result = spectral_rows.T
    result.index = wavelengths
    result.index.name = ""
    result.columns = [f"{float(value):g}" for value in process_time]
    return result.dropna(how="all").sort_index()


def _parse_exported_text(content: bytes, file_name: str | None) -> pd.DataFrame:
    text = _decode_text(content, file_name)
    if not text.strip():
        return pd.DataFrame()

    table = pd.read_csv(StringIO(text), sep=None, engine="python", comment="#")
    return _table_to_spectral_df(table)


def _parse_exported_excel(content: bytes) -> pd.DataFrame:
    excel_file = pd.ExcelFile(BytesIO(content))
    preferred_sheets = [sheet for sheet in excel_file.sheet_names if sheet not in {"Info", "Summary"}]
    for sheet_name in preferred_sheets + excel_file.sheet_names:
        table = pd.read_excel(excel_file, sheet_name=sheet_name)
        spectral_df = _table_to_spectral_df(table)
        if not spectral_df.empty:
            return spectral_df
    return pd.DataFrame()


def parse_spectral_file(source: bytes | BinaryIO, file_name: str | None = None) -> JascoParseResult:
    """Parse Jasco raw data or FluoroSense spectrum exports."""

    content = _read_bytes(source)
    result = parse_jasco_rawdata(content, file_name)
    if not result.data.empty:
        return result

    lowered_name = (file_name or "").lower()
    try:
        if lowered_name.endswith((".xlsx", ".xlsm", ".xls")):
            data = _parse_exported_excel(content)
        else:
            data = _parse_exported_text(content, file_name)
    except (OSError, ValueError, TypeError, pd.errors.ParserError):
        return result

    if data.empty:
        return result

    warnings = ["Loaded FluoroSense export; only spectral visualization data were imported."]
    header = {"TITLE": _title_from_name(file_name)}
    return JascoParseResult(header, _attach_warnings(data, warnings), {}, warnings)


def parse_jasco_rawdata(source: bytes | BinaryIO, file_name: str | None = None) -> JascoParseResult:
    """Parse a Jasco exported text/CSV file.

    The parser accepts the multi-column time-series exports used by the app and
    intentionally drops ragged data rows so all remaining spectra share one
    complete wavelength grid.
    """

    header: dict[str, str] = {}
    xydata: list[list[str]] = []
    extended_info: dict[str, str] = {}
    warnings: list[str] = []

    mode = "header"
    data_started = False
    data_ended = False

    for raw_line in _read_lines(source):
        line = _decode_line(raw_line, file_name)

        if line.startswith("XYDATA"):
            mode = "data"
            data_started = False
            continue

        if line.startswith("##### Extended Information"):
            mode = "extended"
            data_ended = True
            continue

        if mode == "header":
            if "," in line:
                key, value = line.split(",", 1)
                header[key] = value.rstrip(",")
        elif mode == "data":
            if not line:
                continue
            if line.startswith("#####"):
                mode = "extended"
                data_ended = True
                continue
            if not data_started and "," in line and not line.startswith("#"):
                data_started = True
                xydata.append(line.split(","))
                continue
            if data_started and not data_ended:
                fields = line.split(",")
                if len(fields) >= 2:
                    xydata.append(fields)
        elif mode == "extended" and "," in line:
            key, value = line.split(",", 1)
            extended_info[key.strip()] = value.strip()

    if not xydata or len(xydata) <= 1:
        return JascoParseResult(header, pd.DataFrame(), extended_info, warnings)

    # Multi-column (time-series) exports start the XYDATA section with a column
    # header like ",0,1.7333,...", but single-spectrum exports omit it and begin
    # straight with numeric data such as "300.0000,46.0996". When the first row
    # is itself numeric there is no header to consume.
    header_row = xydata[0]
    if _row_is_all_numeric(header_row):
        columns = None
        data_rows = xydata
    else:
        columns = [str(field).strip() for field in header_row]
        data_rows = xydata[1:]

    expected_fields = len(header_row)
    complete_rows = []
    skipped_rows = 0
    for row in data_rows:
        if len(row) == expected_fields:
            complete_rows.append(row)
        else:
            skipped_rows += 1

    if skipped_rows:
        warnings.append(f"{skipped_rows} incomplete wavelength row(s) skipped.")

    if not complete_rows:
        return JascoParseResult(header, pd.DataFrame(), extended_info, warnings)

    df = pd.DataFrame(complete_rows, columns=columns)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # The first XYDATA column is always the wavelength (x) axis: the unnamed ""
    # column for time-series exports and the leading wavelength column for
    # headerless single spectra. Use it as the index either way.
    df.set_index(df.columns[0], inplace=True)
    df.index.name = ""

    df = df.dropna(how="all")
    df.index = pd.to_numeric(df.index, errors="coerce")
    df = df[~pd.isna(df.index)]

    expected_points = _header_int(header, "NPOINTS")
    actual_points = len(df.index)
    if actual_points and expected_points and actual_points != expected_points:
        warnings.append(f"Incomplete spectrum: {actual_points}/{expected_points} wavelength points.")

    expected_first = _header_float(header, "FIRSTX")
    expected_last = _header_float(header, "LASTX")
    if actual_points and expected_first is not None and expected_last is not None:
        actual_first = float(np.nanmin(df.index.values))
        actual_last = float(np.nanmax(df.index.values))
        if not np.isclose(actual_first, expected_first) or not np.isclose(actual_last, expected_last):
            warnings.append(
                f"Range {actual_first:g}-{actual_last:g} nm; expected {expected_first:g}-{expected_last:g} nm."
            )

    return JascoParseResult(header, _attach_warnings(df, warnings), extended_info, warnings)


def parse_warnings(df: pd.DataFrame) -> list[str]:
    """Return parser warnings attached to a dataframe."""

    return list(df.attrs.get("parse_warnings", [])) if hasattr(df, "attrs") else []


def as_individual_spectrum(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize parsed single-spectrum data to wavelength/intensity columns."""

    if df.empty:
        return pd.DataFrame(columns=["Wavelength [nm]", "Intensity"])

    if {"Wavelength [nm]", "Intensity"}.issubset(df.columns):
        result = pd.DataFrame(
            {
                "Wavelength [nm]": pd.to_numeric(df["Wavelength [nm]"], errors="coerce"),
                "Intensity": pd.to_numeric(df["Intensity"], errors="coerce"),
            }
        )
        return _copy_attrs(df, result.dropna(how="any").reset_index(drop=True))

    numeric_df = df.select_dtypes(include=["number"])
    if numeric_df.empty:
        return pd.DataFrame(columns=["Wavelength [nm]", "Intensity"])

    if isinstance(numeric_df.index, pd.RangeIndex) and len(numeric_df.columns) >= 2:
        wavelength_col = numeric_df.columns[0]
        intensity_col = numeric_df.columns[1]
        wavelengths = pd.to_numeric(numeric_df[wavelength_col], errors="coerce")
        if wavelengths.is_monotonic_increasing and wavelengths.notna().any():
            result = pd.DataFrame(
                {
                    "Wavelength [nm]": wavelengths,
                    "Intensity": pd.to_numeric(numeric_df[intensity_col], errors="coerce"),
                }
            )
            return _copy_attrs(df, result.dropna(how="any").reset_index(drop=True))

    intensity_col = numeric_df.columns[0]
    result = pd.DataFrame(
        {
            "Wavelength [nm]": pd.to_numeric(numeric_df.index, errors="coerce"),
            "Intensity": pd.to_numeric(numeric_df[intensity_col], errors="coerce"),
        }
    )
    result = result.dropna(how="any").reset_index(drop=True)
    return _copy_attrs(df, result)
