"""Finnhub market-news sources.

One free Finnhub news pull powers two signals:
  fetch_ceo()     — an influential person (config.WATCHED_PEOPLE) named favorably
  fetch_analyst() — an analyst / major bank upgrade or raised price target

Get a free key at https://finnhub.io and set FINNHUB_API_KEY.
"""
import requests

from bot import config

NEWS = "https://finnhub.io/api/v1/news"  # general US market news feed

_cache = None  # avoid two HTTP calls when running both sources in one run


def _news():
    global _cache
    if _cache is not None:
        return _cache
    if not config.FINNHUB_API_KEY:
        print("[finnhub] FINNHUB_API_KEY not set; CEO + analyst sources skipped")
        _cache = []
        return _cache
    try:
        r = requests.get(NEWS, params={"category": "general", "token": config.FINNHUB_API_KEY}, timeout=20)
        r.raise_for_status()
        _cache = r.json() or []
    except Exception as e:
        print(f"[finnhub] fetch failed: {e}")
        _cache = []
    return _cache


def _text(item):
    return f"{item.get('headline', '')} {item.get('summary', '')}".lower()


def _base(item, kind, uid_prefix):
    text = _text(item)
    return {
        "id": f"{uid_prefix}:{item.get('id') or item.get('url')}",
        "kind": kind,
        "title": item.get("headline", ""),
        "detail": (item.get("summary", "") or "")[:400],
        "url": item.get("url", ""),
        "tickers": [item["related"]] if item.get("related") else [],
        "_text": text,  # marks this as a news alert eligible for the optional LLM filter
    }


def fetch_ceo(state):
    alerts = []
    for item in _news():
        text = _text(item)
        person = next(
            (name for name, aliases in config.WATCHED_PEOPLE.items() if any(a in text for a in aliases)),
            None,
        )
        if not person:
            continue
        if not any(cue in text for cue in config.POSITIVE_CUES):
            continue
        a = _base(item, f"{person} 開金口", "finnhub-ceo")
        alerts.append(a)
    return alerts


def fetch_analyst(state):
    alerts = []
    for item in _news():
        text = _text(item)
        if not any(cue in text for cue in config.UPGRADE_CUES):
            continue
        # Require a bank name or an explicit "price target" to cut generic noise.
        if not (any(b in text for b in config.BANKS) or "price target" in text or "目標價" in text or "目标价" in text):
            continue
        alerts.append(_base(item, "分析師/大行升評", "finnhub-analyst"))
    return alerts
