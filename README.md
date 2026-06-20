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

```python
from afterquote import SecurityPair

pair = SecurityPair("3USL.L", "SPY")
print(pair.info())
print(pair.pricing())
```

## Example Output
```text
                          base_security underlying_security  base_is_live  leverage           base_close_time  base_close_price  adj_percent_return  quote_price
quote_time
2026-06-19 00:59:00+01:00        3USL.L                 SPY         False         3 2026-06-18 16:30:00+01:00        177.869995            0.621451   178.975369
```

```text
                            Impl_Open   Impl_High    Impl_Low  Impl_Close
Datetime
2026-06-18 16:30:00+01:00  177.869995  178.077587  177.733974  178.070422
2026-06-18 16:31:00+01:00  178.070422  178.185074  177.941470  177.941470
2026-06-18 16:32:00+01:00  177.927178  177.962971  177.769626  177.884217
2026-06-18 16:33:00+01:00  177.884217  177.934294  177.619327  177.741023
2026-06-18 16:34:00+01:00  177.762466  178.141756  177.762466  177.991464
...                                ...          ...          ...          ...
2026-06-19 00:55:00+01:00  179.061663  179.147951  179.040091  179.090425
2026-06-19 00:56:00+01:00  179.083234  179.131847  178.953792  179.004130
2026-06-19 00:57:00+01:00  179.004130  179.032887  178.982563  179.004130
2026-06-19 00:58:00+01:00  178.986158  179.025695  178.960997  179.025695
2026-06-19 00:59:00+01:00  179.007721  179.061640  178.946613  178.975369
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
