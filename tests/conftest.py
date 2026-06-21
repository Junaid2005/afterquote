"""Shared test fixtures — fakes yfinance so tests never touch the network."""

import pandas as pd
import pytz
import pytest

from afterquote._security_pair import SecurityPair


class FakeYFinanceSecurity:
    """Drop-in replacement for YFinanceSecurity with hardcoded data."""

    def __init__(self, ticker, info, history_df):
        self.ticker = ticker
        self._info = info
        self._history = history_df
        self.yf_ticker = (
            self  # pricing() calls self.underlying_yf.yf_ticker.history(...)
        )

    def history(self, start=None, end=None, interval="1m", prepost=True):
        return self._history

    def is_real_security(self) -> bool:
        return bool(self._info.get("longName"))

    def get_leverage(self) -> int:
        return self._info.get("leverage", 1)

    def get_timezone(self):
        return pytz.timezone(self._info["timeZoneFullName"])

    def get_currency(self) -> str:
        return self._info.get("currency", "USD").upper()

    def get_exchange(self) -> str:
        return self._info["exchange"]

    def get_price_at(self, timestamp: pd.Timestamp) -> pd.Series:
        if timestamp in self._history.index:
            return self._history.loc[[timestamp]].iloc[0]
        return self._history.iloc[-1]


class FakeMarketCalendar:
    """Drop-in replacement for MarketCalendar with fixed open/close state."""

    def __init__(
        self,
        base_open=False,
        underlying_open=True,
        close_time=None,
        tz="America/New_York",
    ):
        self._base_open = base_open
        self._underlying_open = underlying_open
        self._close_time = close_time
        self._tz = tz

    def is_exchange_open(self, exchange, timestamp=None) -> bool:
        if exchange == "LSE":
            return self._base_open
        return self._underlying_open

    def get_closing_time(self, exchange, as_of=None) -> pd.Timestamp:
        return self._close_time

    def get_exchange_tz(self, exchange):
        return pytz.timezone(self._tz)


def make_ohlc(rows, start="2026-06-18 11:30", freq="1min", tz="America/New_York"):
    """Build a fake OHLC DataFrame from a list of (O, H, L, C) tuples."""
    index = pd.date_range(start, periods=len(rows), freq=freq, tz=tz)
    data = {"Open": [], "High": [], "Low": [], "Close": []}
    for o, h, low, c in rows:
        data["Open"].append(o)
        data["High"].append(h)
        data["Low"].append(low)
        data["Close"].append(c)
    return pd.DataFrame(data, index=index)


def make_security_pair(
    base_info,
    base_history,
    underlying_info,
    underlying_history,
    base_open=False,
    underlying_open=True,
    close_time=None,
    tz="America/New_York",
    fx_history=None,
):
    """Build a SecurityPair with fakes wired in — no network calls."""
    pair = SecurityPair.__new__(SecurityPair)
    pair.base_yf = FakeYFinanceSecurity("BASE", base_info, base_history)
    pair.underlying_yf = FakeYFinanceSecurity(
        "UNDER", underlying_info, underlying_history
    )
    pair.calendar = FakeMarketCalendar(base_open, underlying_open, close_time, tz)
    # Inject fake FX security when provided — prevents any network calls in FX path
    pair.ccy_pair_yf = (
        FakeYFinanceSecurity("FX", {}, fx_history) if fx_history is not None else None
    )
    return pair


@pytest.fixture
def simple_pair():
    """3-bar underlying, +1% close-to-close each, no gaps, leverage=2, anchor=200."""
    underlying = make_ohlc(
        [
            (100.0, 101.0, 99.5, 101.0),
            (101.0, 102.0, 100.5, 102.0),
            (102.0, 103.0, 101.5, 103.0),
        ]
    )
    base_close_bar = make_ohlc(
        [(200.0, 200.5, 199.5, 200.0)], start="2026-06-18 16:30", tz="Europe/London"
    )
    base_info = {
        "longName": "2x Leveraged Thing",
        "leverage": 2,
        "exchange": "LSE",
        "timeZoneFullName": "Europe/London",
    }
    underlying_info = {
        "longName": "Underlying ETF",
        "leverage": 1,
        "exchange": "PCX",
        "timeZoneFullName": "America/New_York",
    }
    close_time = pd.Timestamp("2026-06-18 16:30:00+01:00")
    return make_security_pair(
        base_info,
        base_close_bar,
        underlying_info,
        underlying,
        base_open=False,
        underlying_open=True,
        close_time=close_time,
    )


def pytest_addoption(parser):
    parser.addoption(
        "--runlive",
        action="store_true",
        default=False,
        help="run tests that hit real yfinance",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runlive"):
        return
    skip_live = pytest.mark.skip(reason="needs --runlive to hit real yfinance")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
