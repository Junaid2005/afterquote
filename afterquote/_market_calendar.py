"""Market calendar logic, to find open/close and trading days"""

from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
import pandas_market_calendars as mcal
import pytz


class UnsupportedExchangeError(KeyError):
    """
    Exception raised when a market calendar name is not found in pandas_market_calendars.

    This usually occurs because yfinance exchange codes do not always match the calendar
    names expected by pandas_market_calendars. If you encounter a missing or unrecognized
    exchange, consider contributing to the exchange mapping in this package to improve coverage.
    """


class MarketCalendar:
    """Encapsulates exchange calendar logic for various exchanges"""

    # Please contribute to this list if you find more exchanges
    # Or find a better way (please) :) - Junaid
    _exchange_map = {
        "NMS": "NASDAQ",
        "NGM": "NASDAQ",
        "BTS": "BATS",
        "PCX": "NYSE",
        "NYQ": "NYSE",
        "AMS": "XAMS",
        "GER": "XFRA",
        "HKG": "XHKG",
        "NSI": "XNSE",
        "TOR": "TSX",
    }

    def __init__(self):
        pass

    def is_exchange_open(
        self,
        yf_exchange_name,
        timestamp: Optional[pd.Timestamp] = None,
    ) -> bool:
        """Checks if an exchange is trading at a given timestamp"""

        if timestamp is None:
            timestamp = pd.Timestamp(datetime.now(pytz.utc))

        cal = self.__get_calendar(yf_exchange_name)
        converted_timestamp = timestamp.tz_convert(cal.tz)
        ts_date = converted_timestamp.date()
        schedule = self.__get_schedule(cal, start=ts_date, end=ts_date)

        try:
            return cal.open_at_time(schedule, converted_timestamp)
        except (ValueError, IndexError):
            return False

    def get_closing_time(
        self, yf_exchange_name: str, as_of: Optional[pd.Timestamp] = None
    ) -> pd.Timestamp:
        """Returns last closing time of the exchange before as_of (or now) in its native timezone"""

        reference = as_of if as_of is not None else pd.Timestamp.now(tz="UTC")
        if reference.tz is None:
            reference = reference.tz_localize("UTC")

        exchange = self.__get_calendar(yf_exchange_name)
        schedule = exchange.schedule(
            start_date=reference.date() - timedelta(days=5),
            end_date=reference.date(),
        )
        recent_closes = schedule[-2:]["market_close"].tolist()
        recent_closes.reverse()

        for close in recent_closes:
            if close < reference:
                return close.astimezone(exchange.tz)

        raise ValueError("Cannot find the last market close")

    def get_exchange_tz(self, yf_exchange_name: str) -> pytz.tzinfo.BaseTzInfo:
        """Returns the timezone for a given exchange"""

        cal = self.__get_calendar(yf_exchange_name)
        return cal.tz

    def __get_calendar(self, yf_exchange_name: str) -> mcal.MarketCalendar:
        """Retrieves a pandas_market_calendars calendar for the given exchange name"""

        try:
            return mcal.get_calendar(
                self._exchange_map.get(yf_exchange_name, yf_exchange_name)
            )
        except RuntimeError as e:
            raise UnsupportedExchangeError(
                f"Could not retrieve calendar for exchange '{yf_exchange_name}'. "
                f"Please consider contributing to this file to add support - Junaid"
            ) from e

    def __get_schedule(
        self,
        exchange_cal: mcal.MarketCalendar,
        start=None,
        end=None,
    ) -> pd.DataFrame:
        """Retrieves a schedule for a pandas market calendar"""
        today = datetime.now().date()
        if start is None:
            start = today
        if end is None:
            end = today
        try:
            return exchange_cal.schedule(
                start_date=start, end_date=end, start="pre", end="post"
            )
        # Handle exchanges with no extended hours
        except ValueError:
            return exchange_cal.schedule(
                start_date=start,
                end_date=end,
            )
