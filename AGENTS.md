# AGENTS.md

## What is this

`afterquote` is a Python package that generates synthetic after-hours price quotes for a financial security based on a correlated underlying asset that's still trading. Useful when one market is closed and the other is open.

## Tech stack

- Python 3.10+
- yfinance (market data), pandas (data), pandas_market_calendars (exchange hours), pytz (timezones)
- ruff (formatting + linting), mypy (type checking), pytest (testing)
- GitHub Actions for CI, PyPI for publishing

## Install

```bash
pip install -e .          # runtime
pip install -e ".[dev]"   # + ruff, mypy
pip install -e ".[test]"  # + pytest
```

## Commands

```bash
ruff format --check .     # format check (CI runs this)
ruff check .              # lint (CI runs this)
mypy afterquote/          # type check (CI runs this)
pytest tests/             # unit tests, mocked, ~0.1s (CI runs this)
pytest tests/ --runlive   # + live yfinance tests (manual, pre-release)
```

## Architecture

Seven modules in `afterquote/`:

- `_yfinance_wrapper.py` — `YFinanceSecurity`: wraps a yfinance ticker. Provides `info`, `leverage`, `exchange`, `timezone`, `currency`, `get_price_at(timestamp)`, `get_history(start, end, interval)`.
- `_market_calendar.py` — `MarketCalendar`: wraps pandas_market_calendars. Maps yfinance exchange codes (NMS, PCX, LSE, etc.) to calendar names. Provides `is_exchange_open`, `get_closing_time`, `get_exchange_tz`.
- `_security_pair.py` — `SecurityPair`: the main API. Holds a base + underlying, produces synthetic quotes. `QuoteInfo` dataclass structures the output. `correlation()` health check. `info(confidence=)` confidence band.
- `_benchmark.py` — `benchmark(pair, days=90)`: daily backtest of synthetic vs actual next-day open. `metrics(results)`: RMSE, MAE, direction hit-rate, tracking error.
- `_holdings.py` — `portfolio_pnl(path, as_of=None)`: CSV/JSON portfolio ingestion with per-position after-hours P&L.
- `_cli.py` — `main(argv=None)`: argparse CLI entrypoint. Flags: `--pricing`, `--benchmark`, `--correlation`, `--confidence`, `--holdings PATH`, `--as-of`. Mode flags are mutually exclusive.

Public API: `SecurityPair(base, underlying)` with `.info()`, `.pricing()`, `.correlation()`. Module-level `benchmark()`, `metrics()`, `portfolio_pnl()`.

## The pricing model

When the base exchange is closed but the underlying is trading, `pricing()` synthesizes OHLC bars for the base by applying the underlying's moves (×leverage) onto the base's last close price.

Key principles:
- **Single anchor** — every synthetic price grows from the base's last **Close** (the settlement), not its Open. One seed, not two.
- **Two legs per bar** — inter-bar gap (underlying open vs prev close) then intra-bar move (underlying close vs its open). Multiplied, not added, because they're sequential.
- **Carry-forward** — `Impl_Open[t] == gap applied to Impl_Close[t-1]`. One continuous chain.
- **Leverage on everything** — Open, High, Low, Close all get the leverage factor. A 3x ETC's entire candle scales 3x.
- **Candles valid by construction** — High/Low/Close all derive from the same `Impl_Open`, so `High >= max(Open,Close) >= Low` always holds.

## FX adjustment

When base and underlying trade in different currencies, `pricing()` fetches the FX rate and applies it as a 1x multiplicative leg alongside the leveraged underlying return. GBp normalised to GBP. Same `_candle_returns` decomposition (gap + intra) shared by both legs.

## Confidence band

`info(confidence=0.95)` attaches `lower_bound`/`upper_bound` from the benchmark's empirical residual percentiles. No Gaussian assumption. First-order: assumes tomorrow's error is drawn from the last ~60 sessions' residuals.

## Correlation health check

`pair.correlation(days=90)` returns Pearson daily-return correlation. Emits `UserWarning` when `|corr| < 0.5`.

## Tests

Tests mock yfinance via `FakeYFinanceSecurity` and `FakeMarketCalendar` in `tests/conftest.py` — no network calls in CI. Live tests in `tests/test_live.py` are skipped unless `--runlive` is passed.

Test data uses hand-computable numbers (e.g. anchor=200, leverage=2, underlying +1% → synthetic 204) so assertions are exact.

## Conventions

- Keep code terse — no excessive variables, no 1-letter names, no comments unless the code isn't self-explanatory
- Commit messages: brief title, optional 1-line description. `type(scope): summary` format (e.g. `fix(pricing): correct OHLC anchoring`)
- One concern per commit, every commit should pass CI
- Follow existing style — ruff handles formatting, don't fight it
- `pyproject.toml` is the source of truth for deps (no requirements.txt)
