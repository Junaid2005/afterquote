# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.3.0] - 2026-06-20

### Fixed

- **OHLC anchoring** — `Impl_Open` and `Impl_Close` now both seed from the base's last close price (single anchor), fixing a phantom gap at t=0 and 99% of invalid candles.
- **Inter-bar gaps** — synthetic pricing now captures the gap between the underlying's prev close and current open, fixing a cumulative return error over long sessions.
- **Ticker validation** — `is_real_security()` now actually rejects fake tickers instead of always returning `True`.
- **Exchange mappings** — added 7 missing mappings (PCX, NYQ, AMS, GER, HKG, NSI, TOR) so common US/EU/Asia tickers work without `UnsupportedExchangeError`.
- **History fetch** — `pricing()` now passes `end=` to yfinance, fixing 0-row returns on newer yfinance versions.
- **Close-price lookup** — widened the lookup window from ±5min to −30min/+5min and returns the nearest bar, fixing crashes on thinly-traded securities.
- **No-data case** — `info()` now returns the base's real close when the underlying has no newer data, instead of crashing with `IndexError`.
- **Leverage on High/Low** — synthetic High/Low now correctly apply the leverage factor (previously un-leveraged).

### Added

- `QuoteInfo` dataclass for structured quote data with `to_frame()` method.
- pytest test suite (17 tests) with mocked yfinance — no network calls in CI.
- Live end-to-end tests (skipped by default, run with `--runlive`).
- ruff for formatting + linting (replaces black + pylint).
- mypy type checking in CI.
- CI now runs tests on Python 3.10, 3.11, 3.12.

### Changed

- Pinned all dependencies with lower bounds to prevent silent breakage from upstream changes.
- CI installs from `pyproject.toml` instead of a stale `requirements.txt` (deleted).

---

## [0.2.1] - 2025-05-18

### Changed

- Updated `README.md` to match changes made in v0.2.0

---

## [0.2.0] - 2025-05-18

### Breaking Changes

- Replaced `SecurityPair.quote()` with a new method `info()` — functionality now split between `info()` (for live/summary state) and `pricing()` (for synthetic quote generation).
- `YFinanceSecurity.get_price_at()` now returns the latest possible `pd.Series` of price data (instead of just `.Open`), enabling richer downstream logic.

### Added

- New `info()` method in `SecurityPair`, summarising live/closed state and quote details.
- New `pricing()` method returns synthetic intraday pricing when the base security is closed.

### Changed

- Improved docstrings, type annotations, and inline comments for clarity and maintainability.

---