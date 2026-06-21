"""Providing a quote for a security from its underlying asset"""

from dataclasses import dataclass, asdict
from typing import Optional

import pandas as pd
from ._yfinance_wrapper import YFinanceSecurity
from ._market_calendar import MarketCalendar


@dataclass
class QuoteInfo:
    base_security: str
    underlying_security: str
    base_is_live: bool
    leverage: int
    quote_time: pd.Timestamp
    base_close_time: Optional[pd.Timestamp] = None
    base_close_price: Optional[float] = None
    adj_percent_return: Optional[float] = None
    quote_price: Optional[float] = None

    def to_frame(self) -> pd.DataFrame:
        data = {k: v for k, v in asdict(self).items() if v is not None}
        df = pd.DataFrame([data])
        df.set_index("quote_time", inplace=True)
        return df


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
        base_ccy = self.base_yf.get_currency()
        underlying_ccy = self.underlying_yf.get_currency()
        if base_ccy != underlying_ccy:
            self.ccy_pair_yf: Optional[YFinanceSecurity] = YFinanceSecurity(
                f"{underlying_ccy}{base_ccy}=X"
            )
        else:
            self.ccy_pair_yf = None

    @staticmethod
    def _candle_returns(
        opens: pd.Series, closes: pd.Series, leverage: int = 1
    ) -> tuple[pd.Series, pd.Series]:
        """Decomposes a price series into (gap_return, intra_return) with optional leverage.

        gap_return  — inter-bar move (open vs prev close), leveraged
        intra_return — intra-bar move (close vs open), leveraged
        """
        gap = (opens / closes.shift()).fillna(1)
        intra = closes / opens
        return 1 + leverage * (gap - 1), 1 + leverage * (intra - 1)

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

    def info(self, as_of: Optional[pd.Timestamp] = None) -> pd.DataFrame:
        """Returns a df with the latest info for the base security"""

        if as_of is None:
            as_of = pd.Timestamp.now(tz="UTC")

        if self.calendar.is_exchange_open(self.base_yf.get_exchange(), as_of):
            last_price_time = self.base_yf.get_price_at(as_of)
            return QuoteInfo(
                base_security=self.base_yf.ticker,
                underlying_security=self.underlying_yf.ticker,
                base_is_live=True,
                leverage=self.base_yf.get_leverage(),
                quote_time=last_price_time.name,
            ).to_frame()

        close_time = self.calendar.get_closing_time(self.base_yf.get_exchange(), as_of)
        close_price = self.base_yf.get_price_at(close_time).Close

        pricing_data = self.pricing(as_of=as_of)

        if pricing_data.empty:
            # Underlying has no trading data after the base's last close — the
            # base is already the most current source, no synthetic is needed.
            return QuoteInfo(
                base_security=self.base_yf.ticker,
                underlying_security=self.underlying_yf.ticker,
                base_is_live=False,
                leverage=self.base_yf.get_leverage(),
                quote_time=close_time,
                base_close_time=close_time,
                base_close_price=close_price,
                quote_price=close_price,
            ).to_frame()

        change = pricing_data["Impl_Close"].iloc[-1] - pricing_data["Impl_Open"].iloc[0]
        leveraged_return = (change / pricing_data["Impl_Open"].iloc[0]) * 100

        return QuoteInfo(
            base_security=self.base_yf.ticker,
            underlying_security=self.underlying_yf.ticker,
            base_is_live=False,
            leverage=self.base_yf.get_leverage(),
            quote_time=pricing_data.index[-1],
            base_close_time=pricing_data.index[0],
            base_close_price=close_price,
            adj_percent_return=leveraged_return,
            quote_price=pricing_data["Impl_Close"].iloc[-1],
        ).to_frame()

    def pricing(
        self, interval: str = "1m", as_of: Optional[pd.Timestamp] = None
    ) -> pd.DataFrame:
        """Returns a df with the calculated extended hours pricing for the base security"""

        if as_of is None:
            as_of = pd.Timestamp.now(tz="UTC")

        if self.calendar.is_exchange_open(self.base_yf.get_exchange(), as_of):
            raise RuntimeError(
                "Cannot compute synthetic return — the base security is already live."
            )

        # Get the last closing time of the base security
        close_time = self.calendar.get_closing_time(self.base_yf.get_exchange(), as_of)
        close_price = self.base_yf.get_price_at(close_time)
        # Convert that to the timezone of the underlying security
        target_timezone = self.calendar.get_exchange_tz(
            self.underlying_yf.get_exchange()
        )
        # The close of the base security is our start for the underlying security
        start_time = close_time.astimezone(target_timezone)
        end_time = as_of.astimezone(target_timezone)

        underlying_pricing = self.underlying_yf.get_history(
            start=start_time, end=end_time, interval=interval
        )

        # Change timezone to that of the base security
        synthetic_pricing = pd.DataFrame(index=underlying_pricing.index)
        synthetic_pricing = synthetic_pricing.tz_convert(
            self.calendar.get_exchange_tz(self.base_yf.get_exchange())
        )

        leverage_factor = self.base_yf.get_leverage()
        anchor_price = close_price["Close"]

        # Gap from the underlying's prev close to this bar's open
        und_gap, und_intra = self._candle_returns(
            underlying_pricing["Open"], underlying_pricing["Close"], leverage_factor
        )

        # FX adjustment: applied as a 1x leg when base and underlying trade in different currencies
        if self.ccy_pair_yf is not None:
            fx_data = (
                self.ccy_pair_yf.get_history(
                    start=start_time, end=end_time, interval=interval
                )
                .reindex(underlying_pricing.index)
                .ffill()
                .bfill()
            )
            # Same gap/intra decomposition as underlying, but always 1x (unhedged assumption)
            fx_gap, fx_intra = self._candle_returns(fx_data["Open"], fx_data["Close"])
        else:
            fx_gap = fx_intra = pd.Series(1.0, index=underlying_pricing.index)

        total_gap = und_gap * fx_gap
        total_return = und_gap * fx_gap * und_intra * fx_intra

        cumulative_close = anchor_price * total_return.cumprod()
        synthetic_pricing["Impl_Open"] = (
            cumulative_close.shift().fillna(anchor_price) * total_gap
        )
        synthetic_pricing["Impl_Close"] = (
            synthetic_pricing["Impl_Open"] * und_intra * fx_intra
        )

        # Scaling the high and low prices
        for col in ["High", "Low"]:
            relative_diff = (
                underlying_pricing[col] - underlying_pricing["Open"]
            ) / underlying_pricing["Open"]
            synthetic_pricing[f"Impl_{col}"] = (
                synthetic_pricing["Impl_Open"]
                * (1 + leverage_factor * relative_diff)
                * fx_intra
            )

        # Reordering column names to match yfinance history method
        synthetic_pricing = synthetic_pricing[
            ["Impl_Open", "Impl_High", "Impl_Low", "Impl_Close"]
        ]

        return synthetic_pricing
