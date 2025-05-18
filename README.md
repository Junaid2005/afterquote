# afterquote

**Synthetic after-hours quote generator based on an asset and its underlying security.**

[![PyPI version](https://img.shields.io/pypi/v/afterquote)](https://pypi.org/project/afterquote/)
[![CI](https://github.com/Junaid2005/afterquote/actions/workflows/pipeline.yml/badge.svg)](https://github.com/Junaid2005/afterquote/actions/workflows/pipeline.yml)

---

## 📦 What is this?

`afterquote` lets you estimate synthetic prices for a financial security based on the real-time performance of a given correlated underlying asset — useful when one market is closed and the other is still trading.

---

## 🚀 Installation

### From PyPI:
```bash
pip install afterquote
```

### Locally:

```bash
pip install -e .
```

## 🧪 Usage

```python
from afterquote import SecurityPair

pair = SecurityPair("MAG5.L", "MAGS")
print(pair.info())
print(pair.pricing())
```

## 📘 Example Output
```text
                          base_security underlying_security  base_is_live  leverage           base_close_time  base_close_price  adj_percent_return  quote_price
quote_time
2025-05-17 00:59:00+01:00        MAG5.L                MAGS         False         5 2025-05-16 16:30:00+01:00            1160.0           -9.524988  1049.510137
```

```text
                             Impl_Open    Impl_High     Impl_Low   Impl_Close
Datetime
2025-05-16 16:30:00+01:00  1160.000000  1161.112373  1160.000000  1160.000000
2025-05-16 16:31:00+01:00  1166.674491  1166.895738  1166.450943  1160.000000
2025-05-16 16:32:00+01:00  1168.417608  1168.417608  1168.068568  1162.845038
2025-05-16 16:33:00+01:00  1168.910139  1169.357836  1168.869835  1164.448536
2025-05-16 16:34:00+01:00  1170.029168  1170.029168  1169.805191  1163.333992
...                                ...          ...          ...          ...
2025-05-17 00:55:00+01:00  1055.186402  1055.934313  1055.108109  1049.593529
2025-05-17 00:56:00+01:00  1054.805236  1054.805236  1054.187307  1049.603777
2025-05-17 00:57:00+01:00  1053.775354  1055.833509  1053.775354  1058.827009
2025-05-17 00:58:00+01:00  1054.804431  1054.804431  1054.186503  1046.453387
2025-05-17 00:59:00+01:00  1051.714787  1052.331267  1051.714787  1049.510137
```

## 🤝 Contributing

Feel free to open issues or submit pull requests if you find bugs or want to improve the package - Junaid :)


## 📄 License

MIT License. See the [LICENSE](./LICENSE) file for full details.
