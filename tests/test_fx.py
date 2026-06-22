"""Tests for FX currency adjustment in synthetic pricing."""

import pandas as pd
import pytest

from tests.conftest import make_ohlc, make_security_pair

BASE_INFO_GBP = {
    "longName": "3x Tesla GBp ETP",
    "leverage": 3,
    "exchange": "LSE",
    "timeZoneFullName": "Europe/London",
    "currency": "GBp",  # pence — normalised to GBP in get_currency()
}
UNDERLYING_INFO_USD = {
    "longName": "Tesla Inc",
    "leverage": 1,
    "exchange": "NMS",
    "timeZoneFullName": "America/New_York",
    "currency": "USD",
}
BASE_INFO_USD = {
    "longName": "3x S&P ETP",
    "leverage": 3,
    "exchange": "LSE",
    "timeZoneFullName": "Europe/London",
    "currency": "USD",
}

_CLOSE_TIME = pd.Timestamp("2026-06-18 16:30:00+01:00")


def _base_close(anchor=100.0):
    return make_ohlc(
        [(anchor, anchor, anchor, anchor)],
        start="2026-06-18 16:30",
        tz="Europe/London",
    )


class TestCurrencyNormalisation:
    """GBp (pence) is normalised to GBP when building the FX ticker."""

    def test_get_currency_uppercase(self):
        from tests.conftest import FakeYFinanceSecurity

        sec = FakeYFinanceSecurity("X", {"currency": "GBp"}, pd.DataFrame())
        assert sec.get_currency() == "GBP"

    def test_get_currency_already_upper(self):
        from tests.conftest import FakeYFinanceSecurity

        sec = FakeYFinanceSecurity("X", {"currency": "USD"}, pd.DataFrame())
        assert sec.get_currency() == "USD"


class TestSameCurrencyNoFxLeg:
    """When base and underlying share a currency, FX leg is a no-op (factor = 1)."""

    def test_same_currency_result_unchanged(self):
        # USD/USD pair — FX should not alter the math
        underlying = make_ohlc([(100.0, 101.0, 99.0, 101.0)])
        pair = make_security_pair(
            BASE_INFO_USD,
            _base_close(200.0),
            UNDERLYING_INFO_USD,
            underlying,
            close_time=_CLOSE_TIME,
        )
        pricing = pair.pricing()
        # leverage=3, underlying +1%, anchor=200 → 200*(1+3*0.01) = 206
        assert pricing["Impl_Close"].iloc[0] == pytest.approx(206.0)


class TestCrossCurrencyFxApplied:
    """FX leg multiplies into the return when currencies differ."""

    def _make_cross_pair(self, underlying_rows, fx_rows, anchor=100.0):
        underlying = make_ohlc(underlying_rows)
        fx = make_ohlc(fx_rows)
        return make_security_pair(
            BASE_INFO_GBP,
            _base_close(anchor),
            UNDERLYING_INFO_USD,
            underlying,
            close_time=_CLOSE_TIME,
            fx_history=fx,
        )

    def test_flat_underlying_fx_move_applies(self):
        # Underlying flat (0%), FX +1% (USD strengthens vs GBP)
        # leverage=3, but FX is 1x: Impl_Close = 100 * 1.0 (underlying) * 1.01 (FX) = 101
        pair = self._make_cross_pair(
            underlying_rows=[(100.0, 100.0, 100.0, 100.0)],
            fx_rows=[(1.0, 1.01, 1.0, 1.01)],
        )
        pricing = pair.pricing()
        assert pricing["Impl_Close"].iloc[0] == pytest.approx(101.0)

    def test_underlying_move_leveraged_fx_not(self):
        # Underlying +1%, FX +1%, leverage=3
        # Expected: anchor * (1 + 3*0.01) * 1.01 = 100 * 1.03 * 1.01 = 104.03
        pair = self._make_cross_pair(
            underlying_rows=[(100.0, 101.0, 99.0, 101.0)],
            fx_rows=[(1.0, 1.01, 1.0, 1.01)],
        )
        pricing = pair.pricing()
        assert pricing["Impl_Close"].iloc[0] == pytest.approx(100 * 1.03 * 1.01)

    def test_fx_weakening_base_reduces_return(self):
        # Underlying +1%, FX -1% (USD weakens vs GBP): GBP return is reduced
        # Expected: 100 * 1.03 * 0.99 = 101.97
        pair = self._make_cross_pair(
            underlying_rows=[(100.0, 101.0, 99.0, 101.0)],
            fx_rows=[(1.0, 1.0, 0.99, 0.99)],
        )
        pricing = pair.pricing()
        assert pricing["Impl_Close"].iloc[0] == pytest.approx(100 * 1.03 * 0.99)

    def test_open_is_anchor_when_no_gap(self):
        # First bar open should still be the anchor (no gap on bar 0)
        pair = self._make_cross_pair(
            underlying_rows=[(100.0, 101.0, 99.0, 101.0)],
            fx_rows=[(1.0, 1.01, 1.0, 1.01)],
        )
        pricing = pair.pricing()
        assert pricing["Impl_Open"].iloc[0] == pytest.approx(100.0)

    def test_high_low_include_fx(self):
        # Underlying High=+2%, Low=-1%, FX +1%, leverage=1
        # Impl_High = anchor * (1 + 1*0.02) * 1.01 = 102 * 1.01 = 103.02
        # Impl_Low  = anchor * (1 + 1*(-0.01)) * 1.01 = 99 * 1.01 = 99.99
        underlying = make_ohlc([(100.0, 102.0, 99.0, 100.0)])
        fx = make_ohlc([(1.0, 1.01, 1.0, 1.01)])
        base_info_1x = {**BASE_INFO_GBP, "leverage": 1}
        pair = make_security_pair(
            base_info_1x,
            _base_close(100.0),
            UNDERLYING_INFO_USD,
            underlying,
            close_time=_CLOSE_TIME,
            fx_history=fx,
        )
        pricing = pair.pricing()
        assert pricing["Impl_High"].iloc[0] == pytest.approx(102.0 * 1.01)
        assert pricing["Impl_Low"].iloc[0] == pytest.approx(99.0 * 1.01)
