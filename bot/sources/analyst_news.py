"""Analyst / research-firm calls on watched tickers — via Google News (free).

Complements the Finnhub analyst source, which only sees Finnhub's US-English general
feed. This searches Google News (any outlet, EN + ZH) for rating / price-target calls
and surfaces those naming a WATCHED_TICKER — catching boutique / Asia / Chinese-media
calls (e.g. Aletheia's Micron $1,600) the Finnhub feed misses. The research firm
(config.BANKS) is tagged when the headline names one.

Capped at one alert per ticker per day (the fastest report) so a heavily-covered call
doesn't flood. News signal → carries "_text" → optional Claude filter.
"""
import datetime
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

from bot import config
from bot.sources.google_news import BASE, _detect_ticker


def fetch(state):
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        hours=config.NEWS_LOOKBACK_HOURS
    )
    cands, seen_links = [], set()
    for query, loc_key in config.ANALYST_NEWS_QUERIES:
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
            print(f"[analyst-gn] query {query!r} failed: {e}")
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
                dt = parsedate_to_datetime(pub)
                if dt < cutoff:
                    continue
            except (TypeError, ValueError):
                dt = cutoff
            low = f"{title} {source}".lower()
            ticker = _detect_ticker(low)
            if not ticker:
                continue
            if not any(cue in low for cue in config.ANALYST_CUES):
                continue
            firm = next((b for b in config.BANKS if b in low), None)
            seen_links.add(link)
            cands.append((dt, ticker, firm, title, source, pub, link, low))

    events = state.setdefault("analyst_events", [])
    events_set = set(events)
    alerts = []
    for dt, ticker, firm, title, source, pub, link, low in sorted(cands, key=lambda c: c[0]):
        # One analyst alert per ticker per day (the fastest report). A big call gets
        # covered by many outlets with varied headlines, so cap by day to stay quiet.
        key = f"{ticker}:{dt.date().isoformat()}"
        if key in events_set:
            continue
        events_set.add(key)
        events.append(key)
        detail = f"📰 最快報導：{source}｜{pub}" if source else f"📰 {pub}"
        if firm:
            detail += f"\n機構：{firm.title()}"
        alerts.append({
            "id": f"analystgn:{key}",
            "kind": f"📊 分析師調評：${ticker}（最快：{source}）" if source else f"📊 分析師調評：${ticker}",
            "title": title,
            "detail": detail,
            "url": link,
            "tickers": [ticker],
            "_text": low,  # eligible for the optional Claude filter
        })
    del events[:-500]
    return alerts
