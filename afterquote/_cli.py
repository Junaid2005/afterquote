"""Terminal entrypoint — afterquote BASE UNDERLYING [--as-of] [--pricing]"""

import argparse
import sys

import pandas as pd

from ._security_pair import SecurityPair


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
        "--pricing",
        action="store_true",
        help="Print full synthetic OHLC bars instead of summary info",
    )

    args = parser.parse_args(argv)

    as_of = pd.Timestamp(args.as_of) if args.as_of else None

    try:
        pair = SecurityPair(args.base, args.underlying)
        result = pair.pricing(as_of=as_of) if args.pricing else pair.info(as_of=as_of)
        print(result.to_string())
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
