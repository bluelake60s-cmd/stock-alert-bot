"""Congressional trades — placeholder source.

The formerly-free public dataset (house-stock-watcher / senate-stock-watcher S3
buckets) now returns HTTP 403, and the remaining feeds require a paid key:
  - Quiver Quant   https://api.quiverquant.com  (needs token)
  - Finnhub        /stock/congressional-trading (premium)
  - FMP            senate/house trading endpoints (premium)

This returns [] so the bot runs cleanly without congress data. When you obtain a
key, implement fetch() to return alert dicts in the same shape as ark.py:
    {"id", "kind", "title", "detail", "url", "tickers": [...]}
Congress filings lag by days, so this is a "direction" signal, not a fast one.
"""


def fetch(state):
    return []
