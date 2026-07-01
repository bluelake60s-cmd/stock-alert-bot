"""Congressional trades via Google News — free coverage of notable members.

The structured congress feeds are all paid or 403 (House/Senate Stock Watcher dead,
FMP/Capitol Trace paid), so instead of buying data we catch the disclosures the way
the Trump-holdings source does: through news. High-profile members — above all Nancy
Pelosi ("the Congress stock queen") — get reported every time they file, so a Google
News search for each watched member (config.CONGRESS_MEMBERS) surfaces the trade for
free. A watched ticker is tagged when the headline names one, but the alert fires
regardless (the disclosure itself is the signal).

Capped at one alert per member per day (the fastest report) so the heavy tracker-site
coverage doesn't flood. It's a news signal → carries "_text" → eligible for the
optional Claude filter.
"""
import datetime
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

from bot import config
from bot.sources.google_news import BASE, _detect_ticker, _sig, seen_or_mark


def fetch(state):
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        hours=config.NEWS_LOOKBACK_HOURS
    )
    cands, seen_links = [], set()
    for query, loc_key in config.CONGRESS_NEWS_QUERIES:
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
            print(f"[congress] query {query!r} failed: {e}")
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
            member = next(
                (name for name, aliases in config.CONGRESS_MEMBERS.items()
                 if any(a in low for a in aliases)),
                None,
            )
            if not member:
                continue
            seen_links.add(link)
            cands.append((dt, member, _detect_ticker(low), title, source, pub, link, low))

    events = state.setdefault("congress_events", [])
    events_set = set(events)
    alerts = []
    for dt, member, ticker, title, source, pub, link, low in sorted(cands, key=lambda c: c[0]):
        # One alert per member per day (fastest report) PLUS a headline fingerprint so an
        # evergreen story doesn't re-send on later days.
        key = f"{member}:{dt.date().isoformat()}"
        if seen_or_mark(events, events_set, key, f"sig:{_sig(title)}"):
            continue
        detail = f"📰 最快報導：{source}｜{pub}" if source else f"📰 {pub}"
        if ticker:
            detail += f"\n提及個股：${ticker}"
        alerts.append({
            "id": f"congressnews:{key}",
            "kind": f"🏛️ 國會交易：{member}（最快：{source}）" if source else f"🏛️ 國會交易：{member}",
            "title": title,
            "detail": detail,
            "url": link,
            "tickers": [ticker] if ticker else [],
            "_text": low,  # eligible for the optional Claude filter
        })
    del events[:-1000]
    return alerts
