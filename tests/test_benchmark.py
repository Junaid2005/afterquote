"""Tests for the benchmark module."""

import numpy as np
import pandas as pd
import pytest

from afterquote._benchmark import benchmark, metrics
from tests.conftest import make_ohlc, make_security_pair


def _make_daily_ohlc(closes, opens=None, start="2026-05-01"):
    """Build a daily OHLC DataFrame from a list of close prices."""
    n = len(closes)
    opens = opens or closes
    rows = [(o, c * 1.01, c * 0.99, c) for o, c in zip(opens, closes)]
    index = pd.bdate_range(start=start, periods=n)
    return pd.DataFrame(
        {
            "Open": [r[0] for r in rows],
            "High": [r[1] for r in rows],
            "Low": [r[2] for r in rows],
            "Close": [r[3] for r in rows],
        },
        index=index,
    )


def _make_benchmark_pair(base_closes, und_closes, leverage=1, fx_closes=None):
    """Wire up a pair with daily history suitable for benchmark()."""
    from tests.conftest import FakeYFinanceSecurity

    base_daily = _make_daily_ohlc(base_closes)
    und_daily = _make_daily_ohlc(und_closes)

    base_info = {
        "longName": "Test Base",
        "leverage": leverage,
        "exchange": "LSE",
        "timeZoneFullName": "Europe/London",
        "currency": "USD",
    }
    und_info = {
        "longName": "Test Und",
        "leverage": 1,
        "exchange": "PCX",
        "timeZoneFullName": "America/New_York",
        "currency": "USD",
    }

    dummy_close = make_ohlc(
        [(100.0, 100.0, 100.0, 100.0)], start="2026-05-01", tz="Europe/London"
    )
    pair = make_security_pair(
        base_info,
        dummy_close,
        und_info,
        und_daily,
        close_time=pd.Timestamp("2026-05-01 16:30:00+01:00"),
    )

    pair.base_yf.yf_ticker = type("T", (), {"history": lambda self, **kw: base_daily})()
    pair.underlying_yf.yf_ticker = type(
        "T", (), {"history": lambda self, **kw: und_daily}
    )()

    if fx_closes is not None:
        fx_daily = _make_daily_ohlc(fx_closes)
        pair.ccy_pair_yf = FakeYFinanceSecurity("FX", {}, fx_daily)
        pair.ccy_pair_yf.yf_ticker = type(
            "T", (), {"history": lambda self, **kw: fx_daily}
        )()

    return pair


class TestBenchmarkOutput:
    def test_returns_dataframe_with_expected_columns(self):
        pair = _make_benchmark_pair(
            base_closes=[100.0] * 6,
            und_closes=[100.0, 101.0, 102.0, 101.0, 103.0, 104.0],
        )
        results = benchmark(pair, days=3)
        assert set(results.columns) == {
            "base_close",
            "synth_open",
            "actual_open",
            "residual",
            "direction_correct",
        }

    def test_respects_days_limit(self):
        pair = _make_benchmark_pair(
            base_closes=[100.0] * 10,
            und_closes=[100.0 + i for i in range(10)],
        )
        results = benchmark(pair, days=5)
        assert len(results) <= 5

    def test_flat_underlying_synth_open_equals_base_close(self):
        # Underlying flat every day → synth_open == base_close (no move)
        pair = _make_benchmark_pair(
            base_closes=[200.0, 200.0, 200.0, 200.0, 200.0],
            und_closes=[100.0, 100.0, 100.0, 100.0, 100.0],
            leverage=1,
        )
        results = benchmark(pair, days=3)
        assert (results["synth_open"] == results["base_close"]).all()

    def test_direction_correct_flag(self):
        pair = _make_benchmark_pair(
            base_closes=[100.0, 110.0, 105.0, 108.0, 112.0],
            und_closes=[100.0, 105.0, 103.0, 106.0, 110.0],
            leverage=1,
        )
        results = benchmark(pair, days=3)
        assert "direction_correct" in results.columns
        assert results["direction_correct"].dtype == bool


class TestMetrics:
    def _make_results(self, residuals, directions):
        return pd.DataFrame(
            {
                "base_close": [100.0] * len(residuals),
                "synth_open": [100.0 + r for r in residuals],
                "actual_open": [100.0] * len(residuals),
                "residual": residuals,
                "direction_correct": directions,
            }
        )

    def test_rmse(self):
        results = self._make_results([3.0, -4.0], [True, False])
        m = metrics(results)
        assert m["rmse"] == pytest.approx(np.sqrt((9 + 16) / 2))

    def test_mae(self):
        results = self._make_results([3.0, -5.0], [True, False])
        m = metrics(results)
        assert m["mae"] == pytest.approx(4.0)

    def test_hit_rate(self):
        results = self._make_results([1.0, -1.0, 1.0], [True, False, True])
        m = metrics(results)
        assert m["direction_correct"] == pytest.approx(2 / 3)

    def test_n(self):
        results = self._make_results([1.0, 2.0, 3.0], [True, True, True])
        assert metrics(results)["n"] == 3
