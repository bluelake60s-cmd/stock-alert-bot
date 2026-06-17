"""Congressional trades — US House + Senate disclosures via Financial Modeling Prep.

Members of Congress must disclose stock trades within 45 days (STOCK Act). We pull
the latest House + Senate disclosure feeds from FMP and alert when a disclosed trade
names one of config.WATCHED_TICKERS — i.e. an insider-adjacent buy/sell in the same
NVIDIA AI ecosystem the rest of the bot tracks (e.g. a House Financial Services member
buying $MRVL before a partnership goes public).

Get a free key at https://financialmodelingprep.com (250 req/day) and set FMP_API_KEY.

Filings lag ~30-45 days, so this is a slow "direction" signal, not a fast one. Like
ARK/SEC it's a FACTUAL event → no "_text" key → it skips the optional LLM filter.

FMP field names differ a little across endpoints/versions, so extraction is tolerant
(symbol|ticker, representative|office|first+last, disclosureDate|dateRecieved, ...).
On a dry run it prints the first row's keys so the real shape is easy to confirm.
"""
import datetime

import requests

from bot import config


def _get(row, *keys):
    """First present, non-empty value among candidate field names."""
    for k in keys:
        v = row.get(k)
        if v not in (None, ""):
            return v
    return ""


def _name(row):
    n = _get(row, "representative", "office", "name")
    if n:
        return n
    full = f"{row.get('firstName', '')} {row.get('lastName', '')}".strip()
    return full or "某國會議員"


def _recent(ddate, cutoff):
    """True if the disclosure date is missing or within the lookback window."""
    if not ddate:
        return True  # keep undated rows; dedup prevents repeats
    try:
        return datetime.date.fromisoformat(str(ddate)[:10]) >= cutoff
    except ValueError:
        return True


def _feed(url, chamber):
    rows = []
    for page in range(config.CONGRESS_MAX_PAGES):
        try:
            r = requests.get(
                url,
                params={"page": page, "limit": 100, "apikey": config.FMP_API_KEY},
                timeout=20,
            )
            r.raise_for_status()
            batch = r.json() or []
        except Exception as e:
            print(f"[congress] {chamber} page {page} fetch failed: {e}")
            break
        if not isinstance(batch, list) or not batch:
            break
        rows.extend(batch)
        if len(batch) < 100:
            break
    return rows


def fetch(state):
    if not config.FMP_API_KEY:
        print("[congress] FMP_API_KEY not set; congress source skipped")
        return []

    cutoff = datetime.date.today() - datetime.timedelta(days=config.CONGRESS_LOOKBACK_DAYS)
    alerts = []
    for chamber, url in config.FMP_CONGRESS_ENDPOINTS.items():
        rows = _feed(url, chamber)
        if config.DRY_RUN and rows:
            print(f"[congress] {chamber}: {len(rows)} rows; sample keys: {sorted(rows[0].keys())}")

        for row in rows:
            symbol = str(_get(row, "symbol", "ticker")).upper().strip()
            if symbol not in config.WATCHED_TICKERS:
                continue
            ddate = _get(row, "disclosureDate", "dateRecieved", "filingDate")
            if not _recent(ddate, cutoff):
                continue

            tdate = _get(row, "transactionDate", "transaction_date")
            ttype = str(_get(row, "type", "transactionType")).lower()
            amount = _get(row, "amount", "range") or "金額未披露"
            name = _name(row)
            link = _get(row, "link", "url", "disclosureUrl")

            if any(w in ttype for w in ("sale", "sell", "賣")):
                action, emoji = "賣出", "🏛️📉"
            elif any(w in ttype for w in ("purchase", "buy", "買")):
                action, emoji = "買入", "🏛️📈"
            else:
                action, emoji = (ttype or "交易"), "🏛️"

            alerts.append({
                "id": f"congress:{symbol}:{tdate}:{name}:{ttype}:{amount}",
                "kind": f"{emoji} 國會{action}（{chamber}）",
                "title": f"{name} {action} ${symbol}",
                "detail": f"金額 {amount}｜交易日 {tdate or '?'}｜披露 {ddate or '?'}",
                "url": link,
                "tickers": [symbol],
            })
    return alerts
