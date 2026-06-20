"""Tests for ticker validation — fake tickers should be rejected."""

import pandas as pd
import pytest

from afterquote._security_pair import SecurityPair
from tests.conftest import FakeYFinanceSecurity, make_ohlc

REAL_INFO = {
    "longName": "Real Thing",
    "leverage": 2,
    "exchange": "LSE",
    "timeZoneFullName": "Europe/London",
}
FAKE_INFO = {
    "longName": None,
    "leverage": 1,
    "exchange": None,
    "timeZoneFullName": None,
}
EMPTY_HIST = pd.DataFrame(columns=["Open", "High", "Low", "Close"])


def _build_pair(base_info, underlying_info):
    """Build a SecurityPair bypassing __init__, with fakes wired in."""
    pair = SecurityPair.__new__(SecurityPair)
    pair.base_yf = FakeYFinanceSecurity("BASE", base_info, EMPTY_HIST)
    pair.underlying_yf = FakeYFinanceSecurity("UNDER", underlying_info, EMPTY_HIST)
    pair.calendar = None  # not used by is_valid_pair
    return pair


class TestValidation:
    def test_fake_pair_rejected(self):
        pair = _build_pair(FAKE_INFO, FAKE_INFO)
        assert pair.is_valid_pair() is False

    def test_mixed_pair_rejected(self):
        pair = _build_pair(REAL_INFO, FAKE_INFO)
        assert pair.is_valid_pair() is False

        pair2 = _build_pair(FAKE_INFO, REAL_INFO)
        assert pair2.is_valid_pair() is False

    def test_real_pair_accepted(self):
        pair = _build_pair(REAL_INFO, REAL_INFO)
        assert pair.is_valid_pair() is True
