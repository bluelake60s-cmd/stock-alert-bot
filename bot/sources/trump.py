"""Trump / Truth Social source — the fastest free Trump signal.

The trade disclosures (OGE / the tracker sites the user listed) are all
after-the-fact and delayed by weeks — useful for long-term reference, not alerts.
The FAST signal is Trump's own Truth Social posts, which routinely move a named
stock within minutes. Truth Social blocks scraping, but trumpstruth.org mirrors
every post as a real RSS feed.

His feed is ~99% political, so the gate is deliberately tight: a post must NAME a
watched company (config.TRUMP_TICKERS) or carry a $CASHTAG. Enable ANTHROPIC_API_KEY
to let Claude catch market-relevant posts this keyword gate would miss.
"""
import datetime
import html
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

from bot import config
from bot.sources.google_news import BASE, _sig, seen_or_mark

CASHTAG = re.compile(r"\$[A-Za-z]{1,5}\b")
_TRUMP_NAMES = ("trump", "特朗普", "川普", "特郎普")

# "intel" usually means intelligence (Trump's most common usage), not Intel Corp.
_INTEL_NOISE = (
    "intelligence", "intel official", "intel community", "intel agency", "ex-intel",
    "intel officer", "intel report", "intel offici", "central intel", "intel chief",
)


def _detect(text):
    for ticker, aliases in config.TRUMP_TICKERS.items():
        for a in aliases:
            a = a.strip().lower()
            if not a:
                continue
            if a.isascii():
                if re.search(rf"\b{re.escape(a)}\b", text):
                    if a == "intel" and any(n in text for n in _INTEL_NOISE):
                        continue  # "intel" = intelligence here, not Intel Corp
                    return ticker
            elif a in text:
                return ticker
    return None


def _clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", " ", s or ""))).strip()


def _truth(state):
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        hours=config.NEWS_LOOKBACK_HOURS
    )
    alerts = []
    try:
        r = requests.get(config.TRUMP_TRUTH_RSS, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception as e:
        print(f"[trump] truth fetch failed: {e}")
        return alerts

    for it in root.iter("item"):
        link = (it.findtext("link") or "").strip()
        pub = it.findtext("pubDate") or ""
        body = _clean(it.findtext("description") or it.findtext("title") or "")
        if not link or not body:
            continue
        try:
            if parsedate_to_datetime(pub) < cutoff:
                continue
        except (TypeError, ValueError):
            pass

        low = body.lower()
        ticker = _detect(low)
        cash = CASHTAG.findall(body)
        if not (ticker or cash):
            continue

        tickers = [ticker] if ticker else []
        for c in cash:
            t = c[1:].upper()
            if t not in tickers:
                tickers.append(t)

        alerts.append({
            "id": f"trump:{link}",
            "kind": "🇺🇸 Trump Truth 貼文（提及個股）",
            "title": body[:180],
            "detail": f"🦅 Trump Truth Social｜{pub}",
            "url": link,
            "tickers": tickers,
            "_text": low,  # eligible for the optional Claude filter
        })
    return alerts


def _holdings_news(state):
    """Trump holdings/trades coverage via Google News — the fastest robust way to
    learn of each new OGE disclosure. Same-day coverage collapses to one alert."""
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        hours=config.NEWS_LOOKBACK_HOURS
    )
    cands, seen_links = [], set()
    for query, loc_key in config.TRUMP_NEWS_QUERIES:
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
            print(f"[trump] news query {query!r} failed: {e}")
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
            if not any(n in low for n in _TRUMP_NAMES):
                continue
            seen_links.add(link)
            cands.append((dt, _detect(low), title, source, pub, link, low))

    events = state.setdefault("gnews_events", [])
    events_set = set(events)
    alerts = []
    for dt, ticker, title, source, pub, link, low in sorted(cands, key=lambda c: c[0]):
        key = f"trump-{ticker or 'hold'}:{dt.date().isoformat()}"
        if seen_or_mark(events, events_set, key, f"sig:{_sig(title)}"):
            continue
        alerts.append({
            "id": f"trumpnews:{_sig(title)}",  # content fingerprint → permanent dedup via `seen`
            "kind": f"🇺🇸 Trump 持倉／動向（最快：{source}）" if source else "🇺🇸 Trump 持倉／動向",
            "title": title,
            "detail": f"📰 最快報導：{source}｜{pub}",
            "url": link,
            "tickers": [ticker] if ticker else [],
            "_text": low,
        })
    del events[:-2000]
    return alerts


def fetch(state):
    return _truth(state) + _holdings_news(state)
