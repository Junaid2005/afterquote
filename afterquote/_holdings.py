"""Portfolio holdings ingestion — CSV/JSON of positions -> after-hours P&L."""

import json
from pathlib import Path
from typing import Optional, Callable

import pandas as pd

from ._security_pair import SecurityPair


def portfolio_pnl(
    path: str | Path,
    as_of: Optional[pd.Timestamp] = None,
    pair_factory: Callable = SecurityPair,
) -> pd.DataFrame:
    """Compute after-hours P&L for a portfolio of positions.

    Input file must have columns: base, underlying, quantity.
    Returns a per-position DataFrame with a totals row appended.
    """
    path = Path(path)
    if path.suffix == ".json":
        positions = pd.DataFrame(json.loads(path.read_text()))
    else:
        positions = pd.read_csv(path)

    required = {"base", "underlying", "quantity"}
    missing = required - set(positions.columns)
    if missing:
        raise ValueError(f"Input file missing columns: {missing}")

    rows = []
    for _, pos in positions.iterrows():
        pair = pair_factory(pos["base"], pos["underlying"])
        info = pair.info(as_of=as_of)

        quote_price = info["quote_price"].iloc[0]
        close_price = info.get("base_close_price", info["quote_price"]).iloc[0]
        pnl = pos["quantity"] * (quote_price - close_price)

        rows.append(
            {
                "base": pos["base"],
                "underlying": pos["underlying"],
                "quantity": pos["quantity"],
                "base_close_price": close_price,
                "quote_price": quote_price,
                "pnl": pnl,
            }
        )

    result = pd.DataFrame(rows)

    total = pd.DataFrame(
        [
            {
                "base": "TOTAL",
                "underlying": "",
                "quantity": result["quantity"].sum(),
                "base_close_price": float("nan"),
                "quote_price": float("nan"),
                "pnl": result["pnl"].sum(),
            }
        ]
    )

    return pd.concat([result, total], ignore_index=True)
