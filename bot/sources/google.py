"""Google / Alphabet as a market mover.

Like the NVIDIA source, but for Alphabet: its AI capital spending and orders lift
suppliers (Broadcom jumped 6% on the $80B AI raise). Alphabet has no clean press
release feed, so we use targeted Google News RSS and gate on an investment/capex
cue. Shares the (ticker, day) event-dedupe log with the google_news source, so one
event collapses to a single fastest alert even across both feeds.
"""
import datetime
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

from bot import config
from bot.sources.google_news import BASE, _detect_ticker

_GOOGLE_NAMES = ("google", "alphabet", "谷歌", "googl")


def fetch(state):
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        hours=config.NEWS_LOOKBACK_HOURS
    )
    cands, seen_links = [], set()
    for query, loc_key in config.GOOGLE_INVEST_QUERIES:
        hl, gl, ceid = config.GOOGLE_NEWS_LOCALES[loc_key]
        try:
            r = requests.get(
                BASE,
                params={"q": query, "hl": hl, "gl": gl, "ceid": ceid},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=20,
            )
            r.raise_for_status()
            root = ET.fromstring(r.content)
        except Exception as e:
            print(f"[ginv] query {query!r} failed: {e}")
            continue

        for it in root.iter("item"):
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            pub = it.findtext("pubDate") or ""
            src_el = it.find("source")
            source = (src_el.text or "").strip() if src_el is not None else ""
            if not title or not link or link in seen_links:
                continue
            try:
                if parsedate_to_datetime(pub) < cutoff:
                    continue
            except (TypeError, ValueError):
                pass
            text = f"{title} {source}".lower()
            if not any(g in text for g in _GOOGLE_NAMES):
                continue
            if not any(cue in text for cue in config.GOOGLE_INVEST_CUES):
                continue
            seen_links.add(link)
            dt = parsedate_to_datetime(pub) if pub else cutoff
            cands.append((dt, _detect_ticker(text) or "GOOGL", title, source, pub, link, text))

    events = state.setdefault("gnews_events", [])
    events_set = set(events)
    alerts = []
    for dt, ticker, title, source, pub, link, text in sorted(cands, key=lambda c: c[0]):
        key = f"{ticker}:{dt.date().isoformat()}"
        if key in events_set:
            continue
        events_set.add(key)
        events.append(key)
        beneficiary = ticker if ticker != "GOOGL" else None
        detail = f"📰 最快報導：{source}｜{pub}"
        if beneficiary:
            detail += f"\n受惠股：${beneficiary}"
        alerts.append({
            "id": f"ginv:{key}",
            "kind": f"Google／Alphabet 投資帶動（最快：{source}）" if source else "Google／Alphabet 投資帶動",
            "title": title,
            "detail": detail,
            "url": link,
            "tickers": [beneficiary] if beneficiary else ["GOOGL"],
            "_text": text,
        })
    del events[:-500]
    return alerts
