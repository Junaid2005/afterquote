"""Tests for SecurityPair.correlation()."""

import random
import warnings

import pandas as pd
import pytest

from tests.conftest import make_ohlc, make_security_pair


def _daily_ohlc(closes, start="2026-01-01"):
    idx = pd.bdate_range(start=start, periods=len(closes))
    return pd.DataFrame(
        {
            "Open": closes,
            "High": [c * 1.01 for c in closes],
            "Low": [c * 0.99 for c in closes],
            "Close": closes,
        },
        index=idx,
    )


def _make_corr_pair(base_closes, und_closes, leverage=1):
    close_bar = make_ohlc(
        [(200.0, 200.5, 199.5, 200.0)],
        start="2026-06-18 16:30",
        tz="Europe/London",
    )
    return make_security_pair(
        {
            "longName": "Base",
            "leverage": leverage,
            "exchange": "LSE",
            "timeZoneFullName": "Europe/London",
            "currency": "USD",
        },
        close_bar,
        {
            "longName": "Und",
            "leverage": 1,
            "exchange": "PCX",
            "timeZoneFullName": "America/New_York",
            "currency": "USD",
        },
        close_bar,
        close_time=pd.Timestamp("2026-06-18 16:30:00+01:00"),
        base_daily=_daily_ohlc(base_closes),
        underlying_daily=_daily_ohlc(und_closes),
    )


class TestCorrelation:
    def test_correlated_pair_returns_high_corr_no_warning(self):
        closes = [100.0 * (1.01**i) for i in range(100)]
        pair = _make_corr_pair(closes, closes)
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            corr = pair.correlation(days=90, warn=True)
        assert corr == pytest.approx(1.0, abs=1e-6)

    def test_uncorrelated_pair_warns(self):
        random.seed(42)
        base = [100.0 + i * 0.1 for i in range(100)]
        und = [100.0 + random.uniform(-1, 1) for _ in range(100)]
        pair = _make_corr_pair(base, und)
        with pytest.warns(UserWarning, match="Low correlation"):
            corr = pair.correlation(days=90, warn=True)
        assert abs(corr) < 0.5

    def test_warn_false_suppresses_warning(self):
        random.seed(42)
        base = [100.0 + i * 0.1 for i in range(100)]
        und = [100.0 + random.uniform(-1, 1) for _ in range(100)]
        pair = _make_corr_pair(base, und)
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            corr = pair.correlation(days=90, warn=False)
        assert abs(corr) < 0.5

    def test_short_history_returns_nan(self):
        closes = [100.0]
        pair = _make_corr_pair(closes, closes)
        corr = pair.correlation(days=90, warn=False)
        assert pd.isna(corr)

    def test_flat_series_returns_nan(self):
        closes = [100.0] * 100
        pair = _make_corr_pair(closes, closes)
        corr = pair.correlation(days=90, warn=False)
        assert pd.isna(corr)
