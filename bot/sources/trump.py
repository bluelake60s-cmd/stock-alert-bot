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

CASHTAG = re.compile(r"\$[A-Za-z]{1,5}\b")

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


def fetch(state):
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        hours=config.NEWS_LOOKBACK_HOURS
    )
    alerts = []
    try:
        r = requests.get(config.TRUMP_TRUTH_RSS, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception as e:
        print(f"[trump] fetch failed: {e}")
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
