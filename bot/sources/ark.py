"""ARK Invest daily trades (Cathie Wood).

Source: arkfunds.io — a free, unofficial API that exposes ARK's published daily
buy/sell activity as clean JSON. No API key required. This is the most reliable
"position change" signal available for free and updates once per US trading day.
"""
import requests

from bot import config

API = "https://arkfunds.io/api/v2/etf/trades"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def fetch(state):
    alerts = []
    for fund in config.ARK_FUNDS:
        try:
            r = requests.get(API, params={"symbol": fund, "limit": 25}, headers=HEADERS, timeout=20)
            r.raise_for_status()
            trades = r.json().get("trades", [])
        except Exception as e:
            print(f"[ark] {fund} fetch failed: {e}")
            continue

        for t in trades:
            direction = (t.get("direction") or "").lower()
            shares = t.get("shares") or 0
            uid = f"ark:{t.get('fund')}:{t.get('date')}:{t.get('ticker')}:{direction}:{shares}"
            tag = "🟢 買入" if direction == "buy" else "🔴 沽出"
            pct = t.get("etf_percent")
            detail = (
                f"{t.get('company', '')}\n"
                f"{tag} {shares:,} 股 · 佔基金 {pct}%\n"
                f"日期 {t.get('date')}"
            )
            alerts.append({
                "id": uid,
                "kind": f"ARK {t.get('fund')} 持倉變動",
                "title": f"{tag}：{t.get('ticker')}",
                "detail": detail,
                "url": f"https://arkfunds.io/funds/{(t.get('fund') or '').lower()}",
                "tickers": [t.get("ticker")] if t.get("ticker") else [],
            })
    return alerts
