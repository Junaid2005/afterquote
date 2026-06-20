"""Tests for info() — the three paths: live, synthetic, no-data."""

import pandas as pd

from tests.conftest import make_ohlc, make_security_pair


class TestInfoLive:
    """When the base exchange is open, info returns base_is_live=True."""

    def test_live_returns_true(self):
        base_close = make_ohlc(
            [(200.0, 200.5, 199.5, 200.0)], start="2026-06-18 16:30", tz="Europe/London"
        )
        pair = make_security_pair(
            {
                "longName": "2x Lev",
                "leverage": 2,
                "exchange": "LSE",
                "timeZoneFullName": "Europe/London",
            },
            base_close,
            {
                "longName": "Under",
                "leverage": 1,
                "exchange": "PCX",
                "timeZoneFullName": "America/New_York",
            },
            base_close,
            base_open=True,
            close_time=pd.Timestamp("2026-06-18 16:30:00+01:00"),
        )
        info = pair.info()
        assert info["base_is_live"].iloc[0] == True
        assert "adj_percent_return" not in info.columns


class TestInfoSynthetic:
    """Normal case: base closed, underlying has data -> synthetic with adj_return."""

    def test_synthetic_has_adj_return(self, simple_pair):
        info = simple_pair.info()
        assert info["base_is_live"].iloc[0] == False
        assert "adj_percent_return" in info.columns
        assert "quote_price" in info.columns

    def test_quote_price_is_last_impl_close(self, simple_pair):
        info = simple_pair.info()
        pricing = simple_pair.pricing()
        assert info["quote_price"].iloc[0] == pricing["Impl_Close"].iloc[-1]


class TestInfoNoData:
    """When underlying has no data after base close, return base close as quote."""

    def test_no_data_returns_base_close(self):
        empty = pd.DataFrame(columns=["Open", "High", "Low", "Close"])
        base_close = make_ohlc(
            [(200.0, 200.5, 199.5, 200.0)], start="2026-06-18 16:30", tz="Europe/London"
        )
        pair = make_security_pair(
            {
                "longName": "2x Lev",
                "leverage": 2,
                "exchange": "LSE",
                "timeZoneFullName": "Europe/London",
            },
            base_close,
            {
                "longName": "Under",
                "leverage": 1,
                "exchange": "PCX",
                "timeZoneFullName": "America/New_York",
            },
            empty,
            close_time=pd.Timestamp("2026-06-18 16:30:00+01:00"),
        )
        info = pair.info()
        assert info["base_is_live"].iloc[0] == False
        assert "adj_percent_return" not in info.columns
        assert info["quote_price"].iloc[0] == info["base_close_price"].iloc[0]
        assert info["quote_price"].iloc[0] == 200.0
