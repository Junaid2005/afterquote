"""Tests for portfolio holdings P&L ingestion."""

import json

import pandas as pd
import pytest

from afterquote._holdings import portfolio_pnl
from tests.conftest import make_ohlc, make_security_pair


def _make_fake_pair(quote_price, close_price, anchor=None):
    """Returns a factory callable that produces a stubbed SecurityPair."""
    underlying = make_ohlc([(100.0, 101.0, 99.0, 101.0)])
    close = make_ohlc(
        [(close_price, close_price, close_price, close_price)],
        start="2026-06-18 16:30",
        tz="Europe/London",
    )
    # Underlying that moves to produce the desired quote_price
    move = (quote_price - close_price) / close_price
    underlying = make_ohlc([(100.0, 101.0, 99.0, 100.0 * (1 + move))])
    info = {
        "longName": "Fake Base",
        "leverage": 1,
        "exchange": "LSE",
        "timeZoneFullName": "Europe/London",
        "currency": "USD",
    }
    und_info = {
        "longName": "Fake Und",
        "leverage": 1,
        "exchange": "PCX",
        "timeZoneFullName": "America/New_York",
        "currency": "USD",
    }
    return make_security_pair(
        info,
        close,
        und_info,
        underlying,
        close_time=pd.Timestamp("2026-06-18 16:30:00+01:00"),
    )


def _write_csv(tmp_path, rows):
    p = tmp_path / "positions.csv"
    pd.DataFrame(rows).to_csv(p, index=False)
    return p


def _write_json(tmp_path, rows):
    p = tmp_path / "positions.json"
    p.write_text(json.dumps(rows))
    return p


class TestPortfolioPnl:
    def test_single_position_pnl(self, tmp_path):
        pair = _make_fake_pair(quote_price=110.0, close_price=100.0)
        path = _write_csv(tmp_path, [{"base": "A", "underlying": "B", "quantity": 10}])
        result = portfolio_pnl(path, pair_factory=lambda b, u: pair)
        pos_row = result[result["base"] == "A"].iloc[0]
        assert pos_row["pnl"] == pytest.approx(10 * (110.0 - 100.0))

    def test_total_row_sums_pnl(self, tmp_path):
        pair1 = _make_fake_pair(110.0, 100.0)
        pair2 = _make_fake_pair(95.0, 100.0)
        pairs = {"A": pair1, "B": pair2}
        path = _write_csv(
            tmp_path,
            [
                {"base": "A", "underlying": "X", "quantity": 10},
                {"base": "B", "underlying": "Y", "quantity": 5},
            ],
        )
        result = portfolio_pnl(path, pair_factory=lambda b, u: pairs[b])
        total = result[result["base"] == "TOTAL"].iloc[0]
        # A: 10*(110-100)=100, B: 5*(95-100)=-25, total=75
        assert total["pnl"] == pytest.approx(75.0)

    def test_json_input(self, tmp_path):
        pair = _make_fake_pair(110.0, 100.0)
        path = _write_json(tmp_path, [{"base": "A", "underlying": "B", "quantity": 2}])
        result = portfolio_pnl(path, pair_factory=lambda b, u: pair)
        assert len(result) == 2  # 1 position + total row

    def test_missing_columns_raises(self, tmp_path):
        path = _write_csv(tmp_path, [{"base": "A", "quantity": 10}])
        with pytest.raises(ValueError, match="missing columns"):
            portfolio_pnl(path, pair_factory=lambda b, u: None)

    def test_result_has_total_row(self, tmp_path):
        pair = _make_fake_pair(105.0, 100.0)
        path = _write_csv(tmp_path, [{"base": "A", "underlying": "B", "quantity": 1}])
        result = portfolio_pnl(path, pair_factory=lambda b, u: pair)
        assert "TOTAL" in result["base"].values

    def test_as_of_passed_through(self, tmp_path):
        """as_of is forwarded to each pair's info() call."""
        calls = []

        class SpyPair:
            def info(self, as_of=None):
                calls.append(as_of)
                return make_security_pair(
                    {
                        "longName": "X",
                        "leverage": 1,
                        "exchange": "LSE",
                        "timeZoneFullName": "Europe/London",
                        "currency": "USD",
                    },
                    make_ohlc(
                        [(100.0, 100.0, 100.0, 100.0)],
                        start="2026-06-18 16:30",
                        tz="Europe/London",
                    ),
                    {
                        "longName": "Y",
                        "leverage": 1,
                        "exchange": "PCX",
                        "timeZoneFullName": "America/New_York",
                        "currency": "USD",
                    },
                    make_ohlc([(100.0, 100.0, 100.0, 100.0)]),
                    close_time=pd.Timestamp("2026-06-18 16:30:00+01:00"),
                ).info()

        path = _write_csv(tmp_path, [{"base": "A", "underlying": "B", "quantity": 1}])
        as_of = pd.Timestamp("2026-06-18 14:00:00-04:00")
        portfolio_pnl(path, as_of=as_of, pair_factory=lambda b, u: SpyPair())
        assert calls[0] == as_of
