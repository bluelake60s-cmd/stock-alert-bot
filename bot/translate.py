"""Optional headline translation to Traditional Chinese.

Uses Google Translate's free, keyless gtx endpoint. Translation is best-effort:
any failure (or a title that's already Chinese / has nothing word-like to
translate) falls back to the original text, so delivery never breaks because of it.
"""
import re

import requests

from bot import config

_ENDPOINT = "https://translate.googleapis.com/translate_a/single"
_CJK = re.compile(r"[一-鿿]")
_WORD = re.compile(r"[A-Za-z]{4,}")


def to_zh(text):
    """Translate text to config.TRANSLATE_TARGET, or return it unchanged when
    translation is disabled, the text is already mostly Chinese, there's nothing
    word-like to translate (codes/tickers/dates), or the call fails."""
    if not text or not config.TRANSLATE_TO_ZH:
        return text
    if len(_CJK.findall(text)) >= max(2, len(text) // 4):
        return text  # already substantially Chinese — don't round-trip it
    if not _WORD.search(text):
        return text  # e.g. "13F-HR · 2026-05-18" — no real words to translate
    try:
        r = requests.get(
            _ENDPOINT,
            params={"client": "gtx", "sl": "auto", "tl": config.TRANSLATE_TARGET, "dt": "t", "q": text},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        r.raise_for_status()
        segments = r.json()[0] or []
        out = "".join(seg[0] for seg in segments if seg and seg[0])
        return out or text
    except Exception as e:
        print(f"[translate] failed: {e}")
        return text
