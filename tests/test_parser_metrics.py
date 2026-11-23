import unittest
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd

from fluorosense.io import as_individual_spectrum, parse_jasco_rawdata, parse_spectral_file, parse_warnings
from fluorosense.metrics import (
    calculate_avg_emission_wavelength,
    calculate_integrals,
    calculate_single_spectrum_aew,
    calculate_single_spectrum_integral,
    calculate_single_spectrum_max_wavelength,
    filter_spectral_range,
    filter_single_spectrum_range,
    spectral_range,
    time_series_wavelength_columns,
)


# Synthetic regression fixture, committed with the repo. It mimics the
# structural quirks of the real instrument files that once broke the parser
# (multi-column time-series, ragged final row, spectrum truncated vs NPOINTS)
# without committing any real experiment data.
SYNTHETIC_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "synthetic_timeseries.csv"
skip_without_fixture = unittest.skipUnless(
    SYNTHETIC_FIXTURE.exists(),
    "Synthetic regression fixture missing from tests/fixtures/",
)


class JascoParserTests(unittest.TestCase):
    @skip_without_fixture
    def test_synthetic_fixture_ragged_row_dropped_and_warned(self):
        result = parse_jasco_rawdata(SYNTHETIC_FIXTURE.read_bytes(), SYNTHETIC_FIXTURE.name)

        self.assertEqual((300.0, 320.0, 21), spectral_range(result.data))
        self.assertEqual((21, 3), result.data.shape)
        self.assertEqual(0, int(result.data.isna().sum().sum()))
        self.assertIn("1 incomplete wavelength row(s) skipped.", result.warnings)
        self.assertIn("Incomplete spectrum: 21/25 wavelength points.", result.warnings)
        self.assertEqual(result.warnings, parse_warnings(result.data))

    @skip_without_fixture
    def test_synthetic_fixture_time_series_metrics_are_numeric(self):
        result = parse_jasco_rawdata(SYNTHETIC_FIXTURE.read_bytes(), SYNTHETIC_FIXTURE.name)
        integrals = calculate_integrals(result.data)
        aew = calculate_avg_emission_wavelength(result.data)

        self.assertEqual(3, len(integrals))
        self.assertEqual(3, len(aew))
        self.assertFalse(integrals.isna().any())
        self.assertFalse(np.isnan(aew).any())

    def test_filter_spectral_range_is_inclusive(self):
        df = pd.DataFrame({"0": [1.0, 2.0, 3.0, 4.0]}, index=[300.0, 310.0, 320.0, 330.0])

        filtered = filter_spectral_range(df, 310.0, 320.0)

        self.assertEqual([310.0, 320.0], filtered.index.tolist())
        self.assertEqual((310.0, 320.0, 2), spectral_range(filtered))

    def test_single_spectrum_helpers_use_shared_metric_logic(self):
        raw = pd.DataFrame({"0": [1.0, 1.0, 2.0]}, index=[300.0, 310.0, 320.0])
        spectrum = as_individual_spectrum(raw)

        self.assertEqual(312.5, calculate_single_spectrum_aew(spectrum))
        self.assertAlmostEqual(70.0 / 3.0, calculate_single_spectrum_integral(spectrum))
        self.assertEqual(320.0, calculate_single_spectrum_max_wavelength(spectrum))

        filtered = filter_single_spectrum_range(spectrum, 310.0, 320.0)
        self.assertEqual([310.0, 320.0], filtered["Wavelength [nm]"].tolist())

    def test_individual_spectrum_uses_explicit_wavelength_column(self):
        raw = pd.DataFrame({"Wavelength": [300.0, 310.0, 320.0], "Signal": [10.0, 20.0, 30.0]})

        spectrum = as_individual_spectrum(raw)

        self.assertEqual([300.0, 310.0, 320.0], spectrum["Wavelength [nm]"].tolist())
        self.assertEqual([10.0, 20.0, 30.0], spectrum["Intensity"].tolist())

    def test_individual_spectrum_preserves_export_columns(self):
        raw = pd.DataFrame({"Wavelength [nm]": [300.0, 310.0], "Intensity": [11.0, 22.0]})

        spectrum = as_individual_spectrum(raw)

        self.assertEqual([300.0, 310.0], spectrum["Wavelength [nm]"].tolist())
        self.assertEqual([11.0, 22.0], spectrum["Intensity"].tolist())

    def test_parse_headerless_single_spectrum_jasco_raw(self):
        # Real Jasco single-spectrum exports have no column header in the XYDATA
        # section: the first row after "XYDATA" is numeric data. The first
        # wavelength point must be kept and intensity must not collapse onto the
        # wavelength axis (regression for the slope-1 "linear line" plot bug).
        raw = (
            b"TITLE,0.4 M\n"
            b"XUNITS,NANOMETERS\n"
            b"YUNITS,INTENSITY\n"
            b"FIRSTX,  300.0000\n"
            b"LASTX,  305.0000\n"
            b"NPOINTS,     11\n"
            b"XYDATA\n"
            b"300.0000,46.0996\n"
            b"300.5000,50.0778\n"
            b"301.0000,54.3144\n"
            b"301.5000,58.8205\n"
            b"302.0000,63.7031\n"
            b"302.5000,69.3096\n"
            b"303.0000,75.565\n"
            b"303.5000,82.3133\n"
            b"304.0000,89.4886\n"
            b"304.5000,97.1877\n"
            b"305.0000,105.834\n"
            b"##### Extended Information\n"
        )

        result = parse_spectral_file(raw, "0.4 M.csv")
        spectrum = as_individual_spectrum(result.data)

        self.assertEqual(11, len(spectrum))
        self.assertEqual([300.0, 300.5, 305.0], [spectrum["Wavelength [nm]"].iloc[0],
                                                  spectrum["Wavelength [nm]"].iloc[1],
                                                  spectrum["Wavelength [nm]"].iloc[-1]])
        self.assertEqual([46.0996, 105.834], [spectrum["Intensity"].iloc[0],
                                              spectrum["Intensity"].iloc[-1]])
        # The first data point must not be silently dropped as a "header".
        self.assertEqual("0.4 M", result.header["TITLE"])
        self.assertNotIn("Incomplete spectrum", "\n".join(result.warnings))
        # Intensity is not the wavelength axis re-plotted (the original symptom).
        self.assertFalse(spectrum["Intensity"].equals(spectrum["Wavelength [nm]"]))

    def test_parse_individual_fluorosense_txt_export(self):
        exported = b"Wavelength [nm]\tIntensity\n300\t10\n310\t20\n320\t30\n"

        result = parse_spectral_file(exported, "sample_processed.txt")
        spectrum = as_individual_spectrum(result.data)

        self.assertEqual("sample_processed", result.header["TITLE"])
        self.assertEqual([300, 310, 320], spectrum["Wavelength [nm]"].tolist())
        self.assertEqual([10, 20, 30], spectrum["Intensity"].tolist())
        self.assertEqual(result.warnings, parse_warnings(result.data))

    def test_parse_time_series_fluorosense_excel_export(self):
        exported = BytesIO()
        processed = pd.DataFrame(
            {
                "Process Time [min]": [0.0, 30.0],
                "300.0": [10.0, 12.0],
                "310.0": [20.0, 22.0],
                "Average emission wavelength [nm]": [306.7, 306.5],
                "Integral": [150.0, 170.0],
                "Max emission wavelength [nm]": [310.0, 310.0],
                "Spectral width [nm]": [4.7, 4.8],
                "Process Time [h]": [0.0, 0.5],
            }
        )
        with pd.ExcelWriter(exported, engine="openpyxl") as writer:
            processed.to_excel(writer, sheet_name="Data", index=False)
            pd.DataFrame({"Value": ["sample"]}, index=["TITLE"]).to_excel(writer, sheet_name="Info")

        result = parse_spectral_file(exported.getvalue(), "sample_processed.xlsx")

        self.assertEqual((300.0, 310.0, 2), spectral_range(result.data))
        self.assertEqual(["0", "30"], result.data.columns.tolist())
        self.assertEqual([10.0, 20.0], result.data["0"].tolist())
        self.assertEqual([12.0, 22.0], result.data["30"].tolist())

    def test_augmented_time_series_wavelength_columns_exclude_metrics(self):
        augmented = pd.DataFrame(
            {
                "Process Time [min]": [0.0],
                "300.0": [10.0],
                "310": [20.0],
                "Average emission wavelength [nm]": [306.7],
                "Integral": [150.0],
                "Max emission wavelength [nm]": [310.0],
                "Spectral width [nm]": [4.7],
                "Process Time [h]": [0.0],
            }
        )

        self.assertEqual(["300.0", "310"], time_series_wavelength_columns(augmented))


if __name__ == "__main__":
    unittest.main()
