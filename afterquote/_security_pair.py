"""Providing a quote for a security from its underlying asset"""

import pandas as pd
from ._yfinance_wrapper import YFinanceSecurity
from ._market_calendar import MarketCalendar


class SecurityPair:
    """Class holding the base asset and its underlying security"""

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

    def info(self) -> pd.DataFrame:
        """Returns a df with the latest info for the base security"""

        if self.calendar.is_exchange_open(self.base_yf.get_exchange()):
            last_price_time = self.base_yf.get_price_at(pd.Timestamp.now())
            df = pd.DataFrame(
                [
                    {
                        "base_security": self.base_yf.ticker,
                        "underlying_security": self.underlying_yf.ticker,
                        "base_is_live": True,  # The base security is currently live
                        "leverage": self.base_yf.get_leverage(),
                        "quote_time": last_price_time.name,
                    }
                ]
            )
            df.set_index("quote_time", inplace=True)
            return df

        # Get the last closing time of the base security
        close_time = self.calendar.get_closing_time(self.base_yf.get_exchange())
        close_price = self.base_yf.get_price_at(close_time).Close

        pricing_data = self.pricing()

        change = pricing_data["Impl_Close"].iloc[-1] - pricing_data["Impl_Open"].iloc[0]
        leveraged_return = (change / pricing_data["Impl_Open"].iloc[0]) * 100

        df = pd.DataFrame(
            [
                {
                    "base_security": self.base_yf.ticker,
                    "underlying_security": self.underlying_yf.ticker,
                    "base_is_live": False,  # The base security is currently closed
                    "leverage": self.base_yf.get_leverage(),
                    "base_close_time": pricing_data.index[0],
                    "base_close_price": close_price,
                    "adj_percent_return": leveraged_return,
                    "quote_time": pricing_data.index[-1],
                    "quote_price": pricing_data["Impl_Close"].iloc[-1],
                }
            ]
        )
        df.set_index("quote_time", inplace=True)
        return df

    def pricing(self, interval: str = "1m") -> pd.DataFrame:
        """Returns a df with the calculated extended hours pricing for the base security"""

        if self.calendar.is_exchange_open(self.base_yf.get_exchange()):
            raise RuntimeError(
                "Cannot compute synthetic return — the base security is already live."
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

        underlying_pricing = self.underlying_yf.yf_ticker.history(
            start=start_time, interval=interval, prepost=True
        )

        # Change timezone to that of the base security
        synthetic_pricing = pd.DataFrame(index=underlying_pricing.index)
        synthetic_pricing = synthetic_pricing.tz_convert(self.calendar.get_exchange_tz(
            self.base_yf.get_exchange()
        ))

        leverage_factor = self.base_yf.get_leverage()

        # Iteratively generate synthetic pricing
        for col in ["Open", "Close"]:
            change_series = underlying_pricing[col].pct_change()
            synthetic_pricing[f"Impl_{col}"] = (
                close_price[col]
                * (1 + (leverage_factor * change_series.fillna(0))).cumprod()
            )

        # Scaling the high and low prices
        for col in ["High", "Low"]:
            relative_diff = (
                underlying_pricing[col] - underlying_pricing["Open"]
            ) / underlying_pricing["Open"]
            synthetic_pricing[f"Impl_{col}"] = synthetic_pricing["Impl_Open"] * (
                1 + (relative_diff)
            )

        # Reordering column names to match yfinance history method
        synthetic_pricing = synthetic_pricing[
            ["Impl_Open", "Impl_High", "Impl_Low", "Impl_Close"]
        ]

        return synthetic_pricing
