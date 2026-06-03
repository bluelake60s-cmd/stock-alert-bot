"""NVIDIA official newsroom source.

NVIDIA's press releases ARE the root event behind the supplier/partner pops the
research traced (the $20B Marvell, $1B Nokia, $5B Intel deals). Catching the
official release is faster and more reliable than waiting for media to relay it.

Gate is tight on purpose: a release passes only if it names a watched-ecosystem
company OR carries a "real money" word (invest / stake / acquire / billion / $),
so routine product announcements don't flood the feed.
"""
import datetime
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

from bot import config
from bot.sources.google_news import _detect_ticker


def fetch(state):
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        hours=config.NEWS_LOOKBACK_HOURS
    )
    alerts = []
    try:
        r = requests.get(config.NVIDIA_NEWSROOM_RSS, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        r.raise_for_status()
        root = ET.fromstring(r.content)
    except Exception as e:
        print(f"[nvidia] fetch failed: {e}")
        return alerts

    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub = it.findtext("pubDate") or ""
        if not title or not link:
            continue
        try:
            if parsedate_to_datetime(pub) < cutoff:
                continue
        except (TypeError, ValueError):
            pass

        text = title.lower()
        ticker = _detect_ticker(text)
        if not (ticker or any(cue in text for cue in config.NVIDIA_MONEY_CUES)):
            continue

        alerts.append({
            "id": f"nvda-pr:{link}",
            "kind": "輝達官方新聞稿（合作／投資）",
            "title": title,
            "detail": f"📢 NVIDIA 官方｜{pub}",
            "url": link,
            "tickers": [ticker] if ticker else [],
            "_text": text,  # eligible for the optional Claude filter
        })
    return alerts
