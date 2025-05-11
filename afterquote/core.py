"""Providing a quote for a security from its underlying asset"""

import pandas as pd
from .yfinance_wrapper import YFinanceSecurity
from .market_calendar import MarketCalendar


class SecurityPair:
    """Class holding the leveraged etf and its underlying security"""

    def __init__(self, base, underlying):
        self.base_yf = YFinanceSecurity(base)
        self.underlying_yf = YFinanceSecurity(underlying)

        if not self.is_valid_pair():
            raise ValueError(
                f"Invalid security pair: {base}, {underlying}",
                "Please use yfinance tickers",
            )

        self.calendar = MarketCalendar()

    def is_valid_pair(self) -> bool:
        """Returns if both of the tickers provided are found by yfinance"""

        return self.underlying_yf.is_real_security() and self.base_yf.is_real_security()

    def is_pair_fully_live(self) -> bool:
        """
        Returns if both of the securities are currently trading,
        meaning no synthetic return is needed
        """

        return self.calendar.is_exchange_open(
            self.base_yf.get_exchange()
        ) and self.calendar.is_exchange_open(self.underlying_yf.get_exchange())

    def quote(self) -> pd.DataFrame:
        """Returns a df with the latest possible quote for the underlying security"""

        if self.is_pair_fully_live():
            raise RuntimeError(
                "Cannot compute synthetic return — both securities are currently trading."
            )

        # Get the last closing time of the base security
        close_time = self.calendar.get_closing_time(self.base_yf.get_exchange())
        close_price = self.base_yf.get_price_at(close_time)
        # Convert that to the timezone of the underlying security
        target_timezone = self.calendar.get_exchange_tz(
            self.underlying_yf.get_exchange()
        )
        # The close of the base security is our start for the underlying security
        start_time = close_time.astimezone(target_timezone)

        # Get the start price of the underlying security
        start_price = self.underlying_yf.get_price_at(start_time)
        # Get the current price of the underlying security
        live_data = self.underlying_yf.yf_ticker.history(
            period="5d", interval="1m", prepost=True
        )
        latest_price = live_data["Close"].iloc[-1]
        latest_time = live_data.index[-1]

        # Calculate the percentage return of the underlying security
        change = latest_price - start_price
        percent_return = (change / start_price) * 100

        leverage_factor = self.base_yf.get_leverage()
        leveraged_return = percent_return * leverage_factor

        # Calculate the quote price based on the leveraged return
        quote_price = close_price * (1 + (leveraged_return / 100))

        return pd.DataFrame(
            [
                {
                    "base_security": self.base_yf.ticker,
                    "underlying_security": self.underlying_yf.ticker,
                    "leverage": leverage_factor,
                    "base_close_time": start_time,
                    "base_close_price": close_price,
                    "adj_percent_return": leveraged_return,
                    "quote_time": latest_time,
                    "quote_price": quote_price,
                }
            ]
        )
