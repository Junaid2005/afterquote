"""Tests for the synthetic pricing algorithm — the core math of afterquote."""

import pandas as pd

from tests.conftest import make_ohlc, make_security_pair


class TestPricingAnchor:
    """The anchor: every synthetic price grows from the base's last close."""

    def test_first_open_is_the_anchor(self, simple_pair):
        pricing = simple_pair.pricing()
        assert pricing["Impl_Open"].iloc[0] == 200.0

    def test_no_phantom_gap_at_t0(self, simple_pair):
        pricing = simple_pair.pricing()
        gap = pricing["Impl_Open"].iloc[0] - pricing["Impl_Close"].iloc[0]
        assert gap != 0  # t0 has an intra-bar move, not a phantom seed gap


class TestPricingChain:
    """The synthetic chain: Open[t] carries from Close[t-1] via the gap."""

    def test_open_carries_from_prev_close(self, simple_pair):
        pricing = simple_pair.pricing()
        for i in range(1, len(pricing)):
            # open_gap is 1.0 (no gap) in simple_pair, so Open[t] == Close[t-1]
            assert pricing["Impl_Open"].iloc[i] == pricing["Impl_Close"].iloc[i - 1]


class TestPricingCandleValidity:
    """Every candle must satisfy High >= max(Open,Close) >= Low."""

    def test_all_candles_valid(self, simple_pair):
        pricing = simple_pair.pricing()
        for i in range(len(pricing)):
            row = pricing.iloc[i]
            assert row["Impl_High"] >= row["Impl_Open"], f"tick {i}: High < Open"
            assert row["Impl_High"] >= row["Impl_Close"], f"tick {i}: High < Close"
            assert row["Impl_Low"] <= row["Impl_Open"], f"tick {i}: Low > Open"
            assert row["Impl_Low"] <= row["Impl_Close"], f"tick {i}: Low > Close"


class TestPricingLeverage:
    """Leverage scales the underlying's moves into the synthetic."""

    def test_close_moves_2x(self, simple_pair):
        # underlying went 100->101 (+1%), leverage=2, anchor=200
        # expected: 200 * (1 + 2*0.01) = 204
        pricing = simple_pair.pricing()
        assert pricing["Impl_Close"].iloc[0] == 204.0

    def test_high_applies_leverage(self, simple_pair):
        # underlying High=101, Open=100 (+1%), leverage=2
        # Impl_High = Impl_Open * (1 + 2*0.01) = 200 * 1.02 = 204
        pricing = simple_pair.pricing()
        assert pricing["Impl_High"].iloc[0] == 204.0

    def test_low_applies_leverage(self, simple_pair):
        # underlying Low=99.5, Open=100 (-0.5%), leverage=2
        # Impl_Low = 200 * (1 + 2*(-0.005)) = 200 * 0.99 = 198
        pricing = simple_pair.pricing()
        assert pricing["Impl_Low"].iloc[0] == 198.0


class TestPricingGap:
    """Inter-bar gaps (underlying open != prev close) are captured."""

    def test_gap_appears_in_synthetic_open(self):
        # underlying bar 1 opens ABOVE bar 0's close (gap up)
        underlying = make_ohlc(
            [
                (100.0, 101.0, 99.0, 100.0),  # flat close
                (102.0, 103.0, 101.0, 102.0),  # opens at 102 (gap up from 100)
            ]
        )
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
            underlying,
            close_time=pd.Timestamp("2026-06-18 16:30:00+01:00"),
        )
        pricing = pair.pricing()
        # tick 0: anchor=200, intra flat (close=open=100), so close=200
        # tick 1: gap = 102/100 - 1 = 0.02, leveraged = 2*0.02 = 0.04
        #         Impl_Open[1] = 200 * (1 + 0.04) = 208
        assert pricing["Impl_Open"].iloc[1] == 208.0


class TestPricingEmpty:
    """Empty underlying data returns empty pricing."""

    def test_empty_underlying_returns_empty(self):
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
        pricing = pair.pricing()
        assert pricing.empty


class TestPricingColumns:
    """Output has the expected columns and order."""

    def test_columns(self, simple_pair):
        pricing = simple_pair.pricing()
        assert list(pricing.columns) == [
            "Impl_Open",
            "Impl_High",
            "Impl_Low",
            "Impl_Close",
        ]
