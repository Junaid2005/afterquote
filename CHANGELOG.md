# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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