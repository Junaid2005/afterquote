# afterquote

**Synthetic after-hours pricing for leveraged and cross-currency securities.**

[![PyPI version](https://img.shields.io/pypi/v/afterquote)](https://pypi.org/project/afterquote/)
[![PyPI downloads](https://static.pepy.tech/badge/afterquote)](https://pepy.tech/projects/afterquote)
[![CI](https://github.com/Junaid2005/afterquote/actions/workflows/pipeline.yml/badge.svg)](https://github.com/Junaid2005/afterquote/actions/workflows/pipeline.yml)

---

The London market closes at 4:30pm. TSLA keeps trading until 9pm EST. If you hold `3TSL.L` — a 3× leveraged ETP in GBp — you have no live price for the next several hours. `afterquote` fills that gap: it synthesises a real-time OHLC quote by applying the underlying's move (with leverage and FX adjustment) to the last known close.

```bash
pip install afterquote
```

```python
from afterquote import SecurityPair

pair = SecurityPair("3TSL.L", "TSLA")
pair.info()
```

```
                                base_security underlying_security  base_is_live  leverage           base_close_time  base_close_price  adj_percent_return  quote_price
quote_time
2026-06-19 00:59:00+01:00        3TSL.L               TSLA         False         3 2026-06-18 16:30:00+01:00        177.869995            0.621451   178.975369
```

---

## How it works

When the base exchange is closed and the underlying is still trading, `afterquote` builds a synthetic quote by decomposing each underlying bar into two multiplicative legs:

- **Gap return** — inter-bar move (underlying open vs its previous close), scaled by leverage
- **Intra return** — intra-bar move (underlying close vs its open), scaled by leverage

For cross-currency pairs (e.g. a GBp ETP tracking a USD stock), the FX rate is fetched and applied as a separate 1× leg — so leverage applies only to the underlying's return, not the currency move.

Every synthetic candle grows from a single anchor (the base's last close), so the chain is continuous and `High ≥ max(Open, Close) ≥ Low` holds by construction.

---

## Usage

### Synthetic quote

```python
pair = SecurityPair("3TSL.L", "TSLA")

pair.info()
```
```
                                base_security underlying_security  base_is_live  leverage           base_close_time  base_close_price  adj_percent_return  quote_price
quote_time
2026-06-19 00:59:00+01:00        3TSL.L               TSLA         False         3 2026-06-18 16:30:00+01:00        177.869995            0.621451   178.975369
```

```python
pair.pricing()
```
```
                              Impl_Open    Impl_High     Impl_Low   Impl_Close
Datetime
2026-06-18 16:30:00+01:00  177.869995  178.077587  177.733974  178.070422
2026-06-18 16:31:00+01:00  178.070422  178.185074  177.941470  177.941470
2026-06-18 16:32:00+01:00  177.927178  177.962971  177.769626  177.884217
2026-06-18 16:33:00+01:00  177.884217  177.934294  177.619327  177.741023
2026-06-18 16:34:00+01:00  177.762466  178.141756  177.762466  177.991464
...
2026-06-19 00:59:00+01:00  178.946613  179.061640  178.946613  178.975369

[509 rows × 4 columns]
```

### Confidence band

```python
pair.info(confidence=0.95)
```
```
                                base_security underlying_security  base_is_live  leverage           base_close_time  base_close_price  adj_percent_return  quote_price  lower_bound  upper_bound
quote_time
2026-06-19 00:59:00+01:00        3TSL.L               TSLA         False         3 2026-06-18 16:30:00+01:00        177.869995            0.621451   178.975369      176.420      181.530
```

`lower_bound` / `upper_bound` come from the empirical distribution of past prediction errors — no Gaussian assumption. The band is asymmetric when errors are skewed.

### Benchmark

```python
from afterquote import benchmark, metrics

results = benchmark(pair, days=90)
print(results)
```
```
            base_close   synth_open  actual_open    residual  direction_correct
2026-03-26  148.320007  163.052340  152.440002    10.612338               True
2026-03-27  152.440002  144.918760  161.800003   -16.881240              False
2026-03-28  161.800003  174.338120  168.220001     6.118119               True
2026-03-31  168.220001  159.774480  163.559998    -3.785518               True
2026-04-01  163.559998  141.832900  129.680008    12.152892               True
...
2026-06-18  177.869995  179.341200  178.240005     1.101195               True

[62 rows × 5 columns]
```

```python
metrics(results)
```
```python
{'rmse': 74.1, 'mae': 58.3, 'direction_correct': 0.71, 'tracking_error': 61.2, 'n': 62}
```

The model called the direction right **71% of the time** over 62 sessions.

### Correlation health check

```python
pair.correlation()
# 0.7612
```

Pearson daily-return correlation between base and underlying over the last 90 days. Emits `UserWarning` when `|corr| < 0.5`.

### Portfolio P&L

`holdings.csv`:
```
base,underlying,quantity
3TSL.L,TSLA,1000
3USL.L,SPY,500
```

```python
from afterquote import portfolio_pnl

portfolio_pnl("holdings.csv")
```
```
     base underlying  quantity  base_close_price  quote_price      pnl
   3TSL.L       TSLA    1000.0        177.869995   178.975369  1105.37
   3USL.L        SPY     500.0        312.540001   313.706240   583.12
    TOTAL                1500.0               NaN          NaN  1688.49
```

### Point-in-time queries

All methods accept `as_of` for historical reconstruction — no look-ahead bias:

```python
pair.info(as_of=pd.Timestamp("2026-06-18 20:00:00-04:00"))
pair.pricing(as_of=pd.Timestamp("2026-06-18 20:00:00-04:00"))
```

---

## CLI

```bash
afterquote 3TSL.L TSLA                                    # synthetic quote
afterquote 3TSL.L TSLA --confidence 0.95                  # with confidence band
afterquote 3TSL.L TSLA --pricing                          # full OHLC bars
afterquote 3TSL.L TSLA --benchmark                        # backtest + metrics
afterquote 3TSL.L TSLA --correlation                      # correlation check
afterquote 3TSL.L TSLA --as-of "2026-06-18 20:00-04:00"  # historical query
afterquote --holdings holdings.csv                        # portfolio P&L
```

```
$ afterquote 3TSL.L TSLA --benchmark

            base_close   synth_open  actual_open    residual  direction_correct
2026-03-26  148.320007  163.052340  152.440002    10.612338               True
...
2026-06-18  177.869995  179.341200  178.240005     1.101195               True

  rmse: 74.1
  mae: 58.3
  direction_correct: 0.71
  tracking_error: 61.2
  n: 62
```

```
$ afterquote 3TSL.L TSLA --correlation

correlation: 0.7612
```

---

## Demo pairs

| Pair | Leverage | FX | Use case |
|------|----------|----|----------|
| `3TSL.L` / `TSLA` | 3× | GBp → USD | Both leverage and FX active — the full model |
| `3USL.L` / `SPY` | 3× | — | Leverage only — same-currency baseline |

---

## Testing

```bash
pip install -e ".[test]"
pytest tests/          # 68 unit tests, mocked, ~0.4s — no network calls
pytest tests/ --runlive  # + live yfinance validation
```

---

## Contributing

Issues and PRs welcome. — Junaid

## License

MIT. See [LICENSE](./LICENSE).
