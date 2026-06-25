"""Google News RSS source — bilingual (中／英), fast for live events.

The research takeaway: the market-moving moments are live keynotes (Computex, GTC)
and TV hits, and for Asia-based events the Chinese/Taiwan media report hours before
English outlets. Finnhub's US/English feed misses that. Google News RSS search is
free, carries pubDate timestamps, and covers every outlet in any language — so a
query for "黃仁勳" surfaces 經濟日報／中央社／風傳媒 within minutes of a Computex line.

Relevance gate: a watched person must appear, AND either a positive/endorsement cue
or a watched-ecosystem company name. The optional Claude filter then makes the final
call (set ANTHROPIC_API_KEY — strongly recommended here, this feed is noisy).
"""
import datetime
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

from bot import config

BASE = "https://news.google.com/rss/search"


def _detect_ticker(text):
    """Match a watched company. Latin aliases use word boundaries so "intel" does
    NOT match "intelligence"; CJK aliases (no word boundaries) match as substrings."""
    for ticker, aliases in config.WATCHED_TICKERS.items():
        for a in aliases:
            a = a.strip().lower()
            if not a:
                continue
            if a.isascii():
                if re.search(rf"\b{re.escape(a)}\b", text):
                    return ticker
            elif a in text:
                return ticker
    return None


def _sig(title):
    """Normalized headline fingerprint: drop the trailing ' - Outlet', keep only
    letters/digits/CJK, take the first 48 chars. Lets the SAME story collapse to one
    alert across different outlets AND across days (their headlines are ~identical)."""
    t = re.sub(r"\s*[-|｜–—]\s*[^-|｜–—]+$", "", title.lower())
    return re.sub(r"[^0-9a-z一-鿿]+", "", t)[:48]


def _pubdt(pub, cutoff):
    """Parsed datetime if within window, else None (None also for unparseable-old)."""
    try:
        dt = parsedate_to_datetime(pub)
    except (TypeError, ValueError):
        return cutoff  # unknown time: treat as borderline-fresh so it isn't dropped
    return dt if dt >= cutoff else None


def fetch(state):
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        hours=config.NEWS_LOOKBACK_HOURS
    )
    # Collect every relevant candidate across all queries first, so we can keep only
    # the earliest (fastest) report per event.
    cands, seen_links = [], set()
    for query, loc_key in config.GOOGLE_NEWS_QUERIES:
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
            print(f"[gnews] query {query!r} failed: {e}")
            continue

        for it in root.iter("item"):
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            pub = it.findtext("pubDate") or ""
            src_el = it.find("source")
            source = (src_el.text or "").strip() if src_el is not None else ""
            if not title or not link or link in seen_links:
                continue
            dt = _pubdt(pub, cutoff)
            if dt is None:
                continue
            text = f"{title} {source}".lower()
            person = next(
                (name for name, aliases in config.WATCHED_PEOPLE.items()
                 if any(a in text for a in aliases)),
                None,
            )
            if not person:
                continue
            ticker = _detect_ticker(text)
            # High-signal people (config.GNEWS_PERSON_ONLY) pass on a name match alone;
            # everyone else still needs a watched ticker or a positive endorsement cue.
            if person not in config.GNEWS_PERSON_ONLY:
                if not (ticker or any(cue in text for cue in config.POSITIVE_CUES)):
                    continue
            seen_links.add(link)
            cands.append((dt, person, ticker, title, source, pub, link, text))

    # Event-level de-dupe: one alert per (ticker, day), keeping the EARLIEST report —
    # so 30 outlets covering one Marvell line collapse to a single "fastest" alert.
    events = state.setdefault("gnews_events", [])
    events_set = set(events)
    alerts = []
    for dt, person, ticker, title, source, pub, link, text in sorted(cands, key=lambda c: c[0]):
        # Ticker stories collapse by (ticker, day); non-ticker stories collapse by a
        # headline fingerprint (date-independent) so the same story across outlets and
        # across days sends only once — previously they were keyed per-link and repeated.
        key = f"{ticker}:{dt.date().isoformat()}" if ticker else f"sig:{_sig(title)}"
        if key in events_set:
            continue
        events_set.add(key)
        events.append(key)
        alerts.append({
            "id": f"gnews:{key}",
            "kind": f"{person} 開金口（最快：{source}）" if source else f"{person} 開金口",
            "title": title,
            "detail": f"📰 最快報導：{source}｜{pub}",
            "url": link,
            "tickers": [ticker] if ticker else [],
            "_text": text,  # eligible for the optional Claude filter
        })
    del events[:-500]  # keep the dedupe log bounded
    return alerts
