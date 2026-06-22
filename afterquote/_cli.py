"""Terminal entrypoint — afterquote BASE UNDERLYING [--as-of] [--confidence] [--pricing] [--benchmark] [--correlation] [--holdings PATH]"""

import argparse
import sys

import pandas as pd

from ._security_pair import SecurityPair
from ._benchmark import benchmark, metrics
from ._holdings import portfolio_pnl


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="afterquote",
        description="Synthetic after-hours quote generator",
    )
    parser.add_argument(
        "base", help="Base security RIC in Yahoo Finance format (e.g. 3TSL.L)"
    )
    parser.add_argument(
        "underlying", help="Underlying RIC in Yahoo Finance format (e.g. TSLA)"
    )
    parser.add_argument(
        "--as-of",
        metavar="TIMESTAMP",
        help="Point-in-time query, e.g. '2026-06-18 14:00:00-04:00'",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        metavar="FLOAT",
        help="Attach confidence band (e.g. 0.95) to the info summary",
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--pricing",
        action="store_true",
        help="Print full synthetic OHLC bars instead of summary info",
    )
    mode.add_argument(
        "--benchmark",
        action="store_true",
        help="Run daily backtest and print metrics (RMSE, MAE, hit-rate, etc.)",
    )
    mode.add_argument(
        "--correlation",
        action="store_true",
        help="Print Pearson daily-return correlation between base and underlying",
    )
    mode.add_argument(
        "--holdings",
        metavar="PATH",
        help="CSV or JSON portfolio file (columns: base, underlying, quantity) — prints per-position after-hours P&L",
    )

    args = parser.parse_args(argv)

    as_of = pd.Timestamp(args.as_of) if args.as_of else None

    try:
        if args.holdings:
            result = portfolio_pnl(args.holdings, as_of=as_of)
            print(result.to_string(index=False))
            return

        pair = SecurityPair(args.base, args.underlying)
        if args.benchmark:
            import warnings

            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                results = benchmark(pair)
            print(results.to_string())
            print()
            for key, value in metrics(results).items():
                print(f"  {key}: {value}")
        elif args.pricing:
            result = pair.pricing(as_of=as_of)
            print(result.to_string())
        elif args.correlation:
            corr = pair.correlation()
            print(f"correlation: {corr:.4f}")
        else:
            result = pair.info(as_of=as_of, confidence=args.confidence)
            print(result.to_string())
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
