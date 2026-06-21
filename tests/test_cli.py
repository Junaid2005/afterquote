"""Tests for the CLI entrypoint."""

import pandas as pd
import pytest

from afterquote._cli import main
from tests.conftest import make_ohlc, make_security_pair


def _make_pair(base_open=False):
    underlying = make_ohlc([(100.0, 101.0, 99.5, 101.0)])
    base_close = make_ohlc(
        [(200.0, 200.5, 199.5, 200.0)], start="2026-06-18 16:30", tz="Europe/London"
    )
    info = {
        "longName": "2x Lev",
        "leverage": 2,
        "exchange": "LSE",
        "timeZoneFullName": "Europe/London",
        "currency": "USD",
    }
    und_info = {
        "longName": "Under ETF",
        "leverage": 1,
        "exchange": "PCX",
        "timeZoneFullName": "America/New_York",
        "currency": "USD",
    }
    return make_security_pair(
        info,
        base_close,
        und_info,
        underlying,
        base_open=base_open,
        close_time=pd.Timestamp("2026-06-18 16:30:00+01:00"),
    )


class TestCLIInfo:
    def test_info_prints_output(self, capsys, monkeypatch):
        pair = _make_pair()
        monkeypatch.setattr("afterquote._cli.SecurityPair", lambda b, u: pair)
        main(["BASE", "UNDER"])
        out = capsys.readouterr().out
        assert "base_is_live" in out
        assert "quote_price" in out

    def test_pricing_flag_prints_impl_columns(self, capsys, monkeypatch):
        pair = _make_pair()
        monkeypatch.setattr("afterquote._cli.SecurityPair", lambda b, u: pair)
        main(["BASE", "UNDER", "--pricing"])
        out = capsys.readouterr().out
        assert "Impl_Open" in out
        assert "Impl_Close" in out

    def test_as_of_flag_parsed(self, capsys, monkeypatch):
        pair = _make_pair()
        monkeypatch.setattr("afterquote._cli.SecurityPair", lambda b, u: pair)
        main(["BASE", "UNDER", "--as-of", "2026-06-18 14:00:00-04:00"])
        out = capsys.readouterr().out
        assert len(out) > 0

    def test_bad_ticker_exits_1(self, monkeypatch):
        monkeypatch.setattr(
            "afterquote._cli.SecurityPair",
            lambda b, u: (_ for _ in ()).throw(ValueError("bad ticker")),
        )
        with pytest.raises(SystemExit) as exc:
            main(["BAD", "TICKER"])
        assert exc.value.code == 1
