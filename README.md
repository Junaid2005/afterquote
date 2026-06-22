# afterquote

**Synthetic after-hours quote generator based on an asset and its underlying security.**

[![PyPI version](https://img.shields.io/pypi/v/afterquote)](https://pypi.org/project/afterquote/)
[![PyPI downloads](https://static.pepy.tech/badge/afterquote)](https://pepy.tech/projects/afterquote)
[![CI](https://github.com/Junaid2005/afterquote/actions/workflows/pipeline.yml/badge.svg)](https://github.com/Junaid2005/afterquote/actions/workflows/pipeline.yml)

---

## What is this?

`afterquote` lets you estimate synthetic prices for a financial security based on the real-time performance of a given correlated underlying asset — useful when one market is closed and the other is still trading.

---

## Installation

### From PyPI:
```bash
pip install afterquote
```

### Locally:
```bash
pip install -e .
```

## Usage

### Synthetic quote
```python
from afterquote import SecurityPair

pair = SecurityPair("3TSL.L", "TSLA")
print(pair.info())
print(pair.pricing())
```

### Confidence band
```python
pair = SecurityPair("3TSL.L", "TSLA")
print(pair.info(confidence=0.95))
```
Attaches `lower_bound`/`upper_bound` from the benchmark's empirical residual distribution — no Gaussian assumption.

### Correlation health check
```python
pair = SecurityPair("3TSL.L", "TSLA")
print(pair.correlation())
```
Returns Pearson daily-return correlation. Emits `UserWarning` when `|corr| < 0.5`.

### Benchmark
```python
from afterquote import benchmark, metrics

pair = SecurityPair("3TSL.L", "TSLA")
results = benchmark(pair, days=90)
print(metrics(results))
```

### Holdings P&L
```python
from afterquote import portfolio_pnl

print(portfolio_pnl("holdings.csv"))
```

### CLI
```bash
afterquote 3TSL.L TSLA
afterquote 3TSL.L TSLA --as-of "2026-06-18 19:00"
afterquote 3TSL.L TSLA --pricing
```

## Demo pairs

| Pair | Leverage | FX | Notes |
|------|----------|----|-------|
| `3TSL.L` / `TSLA` | 3x | GBp/USD | Cross-currency flagship — both leverage and FX fire |
| `3USL.L` / `SPY` | 3x | None | Same-currency contrast — leverage only |

## Example output

### `info()`
```text
                          base_security underlying_security  base_is_live  leverage           base_close_time  base_close_price  adj_percent_return  quote_price  lower_bound  upper_bound
quote_time
2026-06-19 00:59:00+01:00        3TSL.L                 TSLA         False         3 2026-06-18 16:30:00+01:00        177.869995            0.621451   178.975369      176.420   181.530
```

### `pricing()`
```text
                            Impl_Open   Impl_High    Impl_Low  Impl_Close
Datetime
2026-06-18 16:30:00+01:00  177.869995  178.077587  177.733974  178.070422
2026-06-18 16:31:00+01:00  178.070422  178.185074  177.941470  177.941470
2026-06-18 16:32:00+01:00  177.927178  177.962971  177.769626  177.884217
...
```

## Testing

```bash
pip install -e ".[test]"
pytest tests/
```

Live tests that hit real yfinance (skipped by default):
```bash
pytest tests/ --runlive
```

## Contributing

Feel free to open issues or submit pull requests if you find bugs or want to improve the package - Junaid :)


## License

MIT License. See the [LICENSE](./LICENSE) file for full details.