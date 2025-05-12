# afterquote

**Synthetic after-hours quote generator based on an asset and its underlying security.**

[![PyPI version](https://img.shields.io/pypi/v/afterquote)](https://pypi.org/project/afterquote/)
[![CI](https://github.com/Junaid2005/afterquote/actions/workflows/pipelines.yml/badge.svg)](https://github.com/Junaid2005/afterquote/actions/workflows/pipelines.yml)

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
quote_df = pair.quote()
print(quote_df)
```

## 📘 Example Output

```text
  base_security underlying_security  leverage           base_close_time  base_close_price  adj_percent_return                 quote_time   quote_price
0        MAG5.L                MAGS         5 2025-05-09 11:30:00-04:00             792.0           -1.044288  2025-05-09 19:59:00-04:00    783.729235
```

## 🤝 Contributing

Feel free to open issues or submit pull requests if you find bugs or want to improve the package - Junaid :)


## 📄 License

MIT License. See the [LICENSE](./LICENSE) file for full details.
