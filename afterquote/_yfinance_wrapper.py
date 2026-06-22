"""Used for querying information and pricing for securities"""

import functools
import re
from datetime import timedelta
import pandas as pd
import pytz
import yfinance as yf


@functools.lru_cache(maxsize=128)
def _fetch_history(
    ticker: str, start: pd.Timestamp, end: pd.Timestamp, interval: str
) -> pd.DataFrame:
    """Cached yfinance history fetch — keyed by ticker + window + interval."""
    return yf.Ticker(ticker).history(
        start=start, end=end, interval=interval, prepost=True
    )


class YFinanceSecurity:
    """Wrapper for yfinance objects"""

    def __init__(self, ticker):
        self.ticker = ticker
        self.yf_ticker = yf.Ticker(ticker)

    def get_history(
        self, start: pd.Timestamp, end: pd.Timestamp, interval: str = "1m"
    ) -> pd.DataFrame:
        """Fetches history for an explicit window — always cached (explicit start/end is deterministic)."""
        return _fetch_history(self.ticker, start, end, interval)

    def is_real_security(self) -> bool:
        """Returns whether yfinance found the ticker"""

        try:
            return bool(self.yf_ticker.info.get("longName"))
        except AttributeError:
            return False

    def get_leverage(self) -> int:
        """Returns the leverage for a security"""

        info = self.yf_ticker.info
        long_name = info.get("longName", "Error finding long name")
        match = re.search(r"(-?\d+x)", long_name)
        if match:
            leverage = match.group(0).replace("x", "")
            if (
                "short" in long_name.lower() or "inverse" in long_name.lower()
            ) and leverage[0] != "-":
                leverage = f"-{leverage}"
            return int(leverage)

        return 1

    def get_timezone(self) -> pytz.tzinfo.BaseTzInfo:
        """Returns a pytz timezone for a security"""

        timezone_name = self.yf_ticker.info.get("timeZoneFullName")
        if not timezone_name:
            raise ValueError(f"Timezone not found for {self.ticker}")
        return pytz.timezone(timezone_name)

    def get_currency(self) -> str:
        """Returns the ISO currency code for a security (normalises GBp -> GBP)"""

        currency = self.yf_ticker.info.get("currency", "")
        if not currency:
            raise ValueError(f"Currency not found for {self.ticker}")
        return currency.upper()

    def get_exchange(self) -> str:
        """Returns the exchange for a security"""

        exchange_name = self.yf_ticker.info.get("exchange")
        if not exchange_name:
            raise ValueError(f"Exchange not found for {self.ticker}")
        return exchange_name

    def get_price_at(self, timestamp: pd.Timestamp) -> pd.Series:
        """Fetches a row of price data closest to the given timestamp using 1m interval data"""

        data = self.yf_ticker.history(
            start=timestamp - timedelta(minutes=30),
            end=timestamp + timedelta(minutes=5),
            interval="1m",
            prepost=True,
        )
        if data.empty:
            raise ValueError(
                f"No pricing data for {self.ticker} found around {timestamp.isoformat()}"
            )
        if timestamp in data.index:
            return data.loc[[timestamp]].iloc[0]  # always returns a Series
        return data.iloc[-1]
