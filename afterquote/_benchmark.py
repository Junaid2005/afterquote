"""Daily backtest — calculated open vs actual next open."""

import numpy as np
import pandas as pd

from ._security_pair import SecurityPair


def benchmark(pair: SecurityPair, days: int = 30) -> pd.DataFrame:
    """Backtest synthetic pricing against actual next-day opens.

    Returns a DataFrame indexed by session date with columns:
        base_close, synth_open, actual_open, residual, direction_correct
    """

    # +30 buffer: calendar days > trading days due to weekends/holidays
    period = f"{days + 30}d"

    base_daily = pair.base_yf.yf_ticker.history(period=period, interval="1d")
    und_daily = pair.underlying_yf.yf_ticker.history(period=period, interval="1d")

    # Strip timezone so LSE (+01:00) and NYSE (-04:00) date labels align
    base_daily.index = base_daily.index.normalize().tz_localize(None)
    und_daily.index = und_daily.index.normalize().tz_localize(None)

    leverage = pair.base_yf.get_leverage()
    und_gap, und_intra = SecurityPair._candle_returns(
        und_daily["Open"], und_daily["Close"], leverage
    )
    und_return = und_gap * und_intra

    if pair.ccy_pair_yf is not None:
        fx_daily = pair.ccy_pair_yf.yf_ticker.history(period=period, interval="1d")
        fx_daily.index = fx_daily.index.normalize().tz_localize(None)
        fx_daily = fx_daily.reindex(und_daily.index).ffill().bfill()
        fx_gap, fx_intra = SecurityPair._candle_returns(
            fx_daily["Open"], fx_daily["Close"]
        )
        fx_return = fx_gap * fx_intra
    else:
        fx_return = pd.Series(1.0, index=und_daily.index)

    daily_returns = und_return * fx_return

    rows = []
    for date, next_date in zip(base_daily.index[:-1], base_daily.index[1:]):
        base_close = base_daily.loc[date, "Close"]
        actual_open = base_daily.loc[next_date, "Open"]

        day_ret = daily_returns.get(date, float("nan"))
        synth_open = base_close * day_ret if not np.isnan(day_ret) else float("nan")
        residual = (
            synth_open - actual_open if not np.isnan(synth_open) else float("nan")
        )
        direction = (
            bool((synth_open - base_close) * (actual_open - base_close) > 0)
            if not np.isnan(synth_open)
            else None
        )

        rows.append(
            {
                "base_close": base_close,
                "synth_open": synth_open,
                "actual_open": actual_open,
                "residual": residual,
                "direction_correct": direction,
            }
        )

    return pd.DataFrame(rows, index=base_daily.index[: len(rows)]).tail(days)


def metrics(results: pd.DataFrame) -> dict:
    """Compute accuracy metrics from benchmark results, skipping NaN rows."""
    valid = results.dropna(subset=["residual", "direction_correct"])
    r = valid["residual"]
    return {
        "rmse": float(np.sqrt((r**2).mean())),
        "mae": float(r.abs().mean()),
        "direction_correct": float(valid["direction_correct"].mean()),
        "tracking_error": float(r.std()),
        "n": len(valid),
    }
