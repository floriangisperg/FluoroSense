import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from fluorosense.io import as_individual_spectrum, parse_jasco_rawdata, parse_warnings
from fluorosense.metrics import (
    calculate_avg_emission_wavelength,
    calculate_integrals,
    calculate_single_spectrum_aew,
    calculate_single_spectrum_integral,
    filter_spectral_range,
    filter_single_spectrum_range,
    spectral_range,
)


REPRODUCE_DIR = Path(__file__).resolve().parents[1] / "data" / "reproduce_bug"


class JascoParserTests(unittest.TestCase):
    def test_reproduce_files_drop_ragged_final_row_and_warn(self):
        for path in sorted(REPRODUCE_DIR.glob("*.csv")):
            with self.subTest(path=path.name):
                result = parse_jasco_rawdata(path.read_bytes(), path.name)

                self.assertEqual((300.0, 363.5, 128), spectral_range(result.data))
                self.assertEqual((128, 661), result.data.shape)
                self.assertEqual(0, int(result.data.isna().sum().sum()))
                self.assertIn("1 incomplete wavelength row(s) skipped.", result.warnings)
                self.assertIn("Incomplete spectrum: 128/301 wavelength points.", result.warnings)
                self.assertIn("Range 300-363.5 nm; expected 300-450 nm.", result.warnings)
                self.assertEqual(result.warnings, parse_warnings(result.data))

    def test_time_series_metrics_are_numeric_for_reproduce_files(self):
        for path in sorted(REPRODUCE_DIR.glob("*.csv")):
            with self.subTest(path=path.name):
                result = parse_jasco_rawdata(path.read_bytes(), path.name)
                integrals = calculate_integrals(result.data)
                aew = calculate_avg_emission_wavelength(result.data)

                self.assertEqual(661, len(integrals))
                self.assertEqual(661, len(aew))
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

        filtered = filter_single_spectrum_range(spectrum, 310.0, 320.0)
        self.assertEqual([310.0, 320.0], filtered["Wavelength [nm]"].tolist())


if __name__ == "__main__":
    unittest.main()
