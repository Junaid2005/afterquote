"""Used for querying information and pricing for securities"""

import re
from datetime import timedelta
import pandas as pd
import pytz
import yfinance as yf


class YFinanceSecurity:
    """Wrapper for yfinance objects"""

    def __init__(self, ticker):
        self.ticker = ticker
        self.yf_ticker = yf.Ticker(ticker)

    def is_real_security(self) -> bool:
        """Returns whether yfinance found the ticker"""

        try:
            self.yf_ticker.info.get("longName")
            return True
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

        info = self.yf_ticker.info
        timezone_name = info.get("timeZoneFullName")
        if not timezone_name:
            raise ValueError(f"Timezone not found for {self.ticker}")
        return pytz.timezone(timezone_name)

    def get_exchange(self) -> str:
        """Returns the exchange for a security"""

        info = self.yf_ticker.info
        exchange_name = info.get("exchange")
        if not exchange_name:
            raise ValueError(f"Exchange not found for {self.ticker}")
        return exchange_name

    def get_price_at(self, timestamp: pd.Timestamp) -> pd.Series:
        """Fetches a row of price data closest to the given timestamp using 1m interval data"""

        data = self.yf_ticker.history(
            start=timestamp - timedelta(minutes=5),
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
        return data.iloc[0]
