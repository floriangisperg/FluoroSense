"""Jasco file parsing helpers."""

from __future__ import annotations

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

    expected_fields = len(xydata[0])
    complete_rows = []
    skipped_rows = 0
    for row in xydata[1:]:
        if len(row) == expected_fields:
            complete_rows.append(row)
        else:
            skipped_rows += 1

    if skipped_rows:
        warnings.append(f"{skipped_rows} incomplete wavelength row(s) skipped.")

    if not complete_rows:
        return JascoParseResult(header, pd.DataFrame(), extended_info, warnings)

    df = pd.DataFrame(complete_rows, columns=xydata[0])
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if "" in df.columns:
        df.set_index("", inplace=True)
    elif len(df.columns) > 0 and str(df.columns[0]).strip() == "":
        df.set_index(df.columns[0], inplace=True)

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

    numeric_df = df.select_dtypes(include=["number"])
    if numeric_df.empty:
        return pd.DataFrame(columns=["Wavelength [nm]", "Intensity"])

    first_col = numeric_df.columns[0]
    result = pd.DataFrame(
        {
            "Wavelength [nm]": pd.to_numeric(numeric_df.index, errors="coerce"),
            "Intensity": pd.to_numeric(numeric_df[first_col], errors="coerce"),
        }
    )
    result = result.dropna(how="any").reset_index(drop=True)
    return _copy_attrs(df, result)
