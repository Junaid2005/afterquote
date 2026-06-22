"""Tests for the confidence band on QuoteInfo."""

import pandas as pd
import pytest

from tests.conftest import make_ohlc, make_security_pair


def _daily_ohlc(closes, opens=None, start="2026-04-01"):
    """Build a tz-naive daily OHLC DataFrame from close prices."""
    n = len(closes)
    opens = opens if opens is not None else closes
    index = pd.bdate_range(start=start, periods=n)
    rows = [(o, c * 1.01, c * 0.99, c) for o, c in zip(opens, closes)]
    return pd.DataFrame(
        {
            "Open": [r[0] for r in rows],
            "High": [r[1] for r in rows],
            "Low": [r[2] for r in rows],
            "Close": [r[3] for r in rows],
        },
        index=index,
    )


def _confidence_pair(base_closes, base_opens, und_closes, leverage=1):
    """Build a pair where intraday underlying is flat (pricing() → quote=anchor)
    and daily history is independently set for benchmark().

    Flat intraday → quote_price always equals the base_close anchor. Daily base
    closes/opens are independent → residuals are exactly controlled.
    """
    base_close_bar = make_ohlc(
        [(200.0, 200.5, 199.5, 200.0)],
        start="2026-06-18 16:30",
        tz="Europe/London",
    )
    flat_intraday = make_ohlc([(100.0, 100.5, 99.5, 100.0)] * 3, freq="1min")
    base_daily = _daily_ohlc(base_closes, opens=base_opens)
    und_daily = _daily_ohlc(und_closes)

    return make_security_pair(
        base_info={
            "longName": "Test Base",
            "leverage": leverage,
            "exchange": "LSE",
            "timeZoneFullName": "Europe/London",
            "currency": "USD",
        },
        base_history=base_close_bar,
        underlying_info={
            "longName": "Test Und",
            "leverage": 1,
            "exchange": "PCX",
            "timeZoneFullName": "America/New_York",
            "currency": "USD",
        },
        underlying_history=flat_intraday,
        close_time=pd.Timestamp("2026-06-18 16:30:00+01:00"),
        base_daily=base_daily,
        underlying_daily=und_daily,
    )


class TestConfidenceBand:
    def test_no_confidence_no_band_columns(self):
        # baseline: lower_bound/upper_bound absent without confidence=
        pair = _confidence_pair(
            base_closes=[100.0] * 5,
            base_opens=[100.0, 99.0, 101.0, 98.0, 102.0],
            und_closes=[100.0] * 5,
        )
        info = pair.info()
        assert "lower_bound" not in info.columns
        assert "upper_bound" not in info.columns
        assert "quote_price" in info.columns

    def test_confidence_attaches_band(self):
        pair = _confidence_pair(
            base_closes=[100.0] * 5,
            base_opens=[100.0, 99.0, 101.0, 98.0, 102.0],
            und_closes=[100.0] * 5,
        )
        info = pair.info(confidence=0.95)
        assert "lower_bound" in info.columns
        assert "upper_bound" in info.columns
        assert "quote_price" in info.columns

    def test_known_residuals_exact_band(self):
        # Flat underlying → synth_open = base_close = 100.
        # base_opens[i+1] = 99, 101, 98, 102 → residuals = [1, -1, 2, -2].
        # quote_price = 200 (anchor). np.percentile([-2,-1,1,2], [2.5,97.5])
        #  -> [-1.925, 1.925] by linear interpolation.
        pair = _confidence_pair(
            base_closes=[100.0] * 5,
            base_opens=[100.0, 99.0, 101.0, 98.0, 102.0],
            und_closes=[100.0] * 5,
        )
        info = pair.info(confidence=0.95)
        quote_price = info["quote_price"].iloc[0]
        assert quote_price == pytest.approx(200.0)
        assert info["lower_bound"].iloc[0] == pytest.approx(200.0 - 1.925)
        assert info["upper_bound"].iloc[0] == pytest.approx(200.0 + 1.925)

    def test_band_asymmetric_for_skewed_residuals(self):
        # residuals = [1, -3, 2, -2] (opens: 99, 103, 98, 102).
        # sorted = [-3, -2, 1, 2]; 2.5pct at -2.925, 97.5pct at 1.925.
        # Asymmetry proves we're not assuming symmetric Gaussian errors.
        pair = _confidence_pair(
            base_closes=[100.0] * 5,
            base_opens=[100.0, 99.0, 103.0, 98.0, 102.0],
            und_closes=[100.0] * 5,
        )
        info = pair.info(confidence=0.95)
        qp = info["quote_price"].iloc[0]
        low, high = info["lower_bound"].iloc[0], info["upper_bound"].iloc[0]
        assert low == pytest.approx(qp - 2.925)
        assert high == pytest.approx(qp + 1.925)
        assert abs(qp - low) != pytest.approx(abs(qp - high))

    def test_band_widens_with_higher_confidence(self):
        # 99% band uses [0.5, 99.5] percentiles -> strictly wider than 95%.
        pair = _confidence_pair(
            base_closes=[100.0] * 5,
            base_opens=[100.0, 99.0, 103.0, 98.0, 102.0],
            und_closes=[100.0] * 5,
        )
        info95 = pair.info(confidence=0.95)
        info99 = pair.info(confidence=0.99)
        w95 = info95["upper_bound"].iloc[0] - info95["lower_bound"].iloc[0]
        w99 = info99["upper_bound"].iloc[0] - info99["lower_bound"].iloc[0]
        assert w99 > w95


class TestBandGates:
    """Band is only attached on the synthetic path."""

    def test_live_path_no_band_even_with_confidence(self):
        base_close_bar = make_ohlc(
            [(200.0, 200.5, 199.5, 200.0)],
            start="2026-06-18 16:30",
            tz="Europe/London",
        )
        pair = make_security_pair(
            base_info={
                "longName": "Live",
                "leverage": 2,
                "exchange": "LSE",
                "timeZoneFullName": "Europe/London",
            },
            base_history=base_close_bar,
            underlying_info={
                "longName": "Under",
                "leverage": 1,
                "exchange": "PCX",
                "timeZoneFullName": "America/New_York",
            },
            underlying_history=base_close_bar,
            base_open=True,
            close_time=pd.Timestamp("2026-06-18 16:30:00+01:00"),
        )
        info = pair.info(confidence=0.95)
        assert bool(info["base_is_live"].iloc[0])
        assert "lower_bound" not in info.columns
        assert "upper_bound" not in info.columns

    def test_no_data_path_no_band_even_with_confidence(self):
        empty = pd.DataFrame(columns=["Open", "High", "Low", "Close"])
        base_close_bar = make_ohlc(
            [(200.0, 200.5, 199.5, 200.0)],
            start="2026-06-18 16:30",
            tz="Europe/London",
        )
        pair = make_security_pair(
            base_info={
                "longName": "X",
                "leverage": 2,
                "exchange": "LSE",
                "timeZoneFullName": "Europe/London",
            },
            base_history=base_close_bar,
            underlying_info={
                "longName": "Y",
                "leverage": 1,
                "exchange": "PCX",
                "timeZoneFullName": "America/New_York",
            },
            underlying_history=empty,
            close_time=pd.Timestamp("2026-06-18 16:30:00+01:00"),
        )
        info = pair.info(confidence=0.95)
        assert "lower_bound" not in info.columns
        assert "upper_bound" not in info.columns

    def test_empty_residuals_raises(self):
        # Empty daily underlying -> every daily_return is NaN -> residuals all
        # NaN -> dropna empty -> _confidence_band raises ValueError.
        empty_daily = pd.DataFrame(
            columns=["Open", "High", "Low", "Close"],
            index=pd.DatetimeIndex([], dtype="datetime64[ns]"),
        )
        base_close_bar = make_ohlc(
            [(200.0, 200.5, 199.5, 200.0)],
            start="2026-06-18 16:30",
            tz="Europe/London",
        )
        flat_intraday = make_ohlc([(100.0, 100.5, 99.5, 100.0)] * 3, freq="1min")
        base_daily = _daily_ohlc([100.0] * 5, opens=[100.0] * 5)
        pair = make_security_pair(
            base_info={
                "longName": "X",
                "leverage": 1,
                "exchange": "LSE",
                "timeZoneFullName": "Europe/London",
                "currency": "USD",
            },
            base_history=base_close_bar,
            underlying_info={
                "longName": "Y",
                "leverage": 1,
                "exchange": "PCX",
                "timeZoneFullName": "America/New_York",
                "currency": "USD",
            },
            underlying_history=flat_intraday,
            base_daily=base_daily,
            underlying_daily=empty_daily,
            close_time=pd.Timestamp("2026-06-18 16:30:00+01:00"),
        )
        with pytest.raises(ValueError, match="no.*valid residual|benchmark"):
            pair.info(confidence=0.95)
