"""Tests for shared utility functions."""

import pandas as pd
import pytest

from scripts.utils import pad_account_code


class TestPadAccountCode:
    """Tests for pad_account_code function."""

    def test_pad_2_digit_codes(self):
        """Test padding 2-digit codes with 2 zeros."""
        codes = pd.Series(["10", "25", "99"])
        result = pad_account_code(codes)
        expected = pd.Series(["0010", "0025", "0099"])
        pd.testing.assert_series_equal(result, expected)

    def test_pad_3_digit_codes(self):
        """Test padding 3-digit codes with 1 zero."""
        codes = pd.Series(["100", "250", "999"])
        result = pad_account_code(codes)
        expected = pd.Series(["0100", "0250", "0999"])
        pd.testing.assert_series_equal(result, expected)

    def test_no_pad_4_digit_codes(self):
        """Test that 4-digit codes remain unchanged."""
        codes = pd.Series(["1000", "2500", "9999"])
        result = pad_account_code(codes)
        expected = pd.Series(["1000", "2500", "9999"])
        pd.testing.assert_series_equal(result, expected)

    def test_mixed_length_codes(self):
        """Test padding mixed length codes."""
        codes = pd.Series(["10", "100", "1000", "25"])
        result = pad_account_code(codes)
        expected = pd.Series(["0010", "0100", "1000", "0025"])
        pd.testing.assert_series_equal(result, expected)

    def test_numeric_codes(self):
        """Test padding numeric codes (converted to string)."""
        codes = pd.Series([10, 100, 1000])
        result = pad_account_code(codes)
        expected = pd.Series(["0010", "0100", "1000"])
        pd.testing.assert_series_equal(result, expected)
