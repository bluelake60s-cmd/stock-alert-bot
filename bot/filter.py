"""Optional LLM relevance filter.

Keyword rules (in the sources) are deliberately loose so nothing is missed. When
ANTHROPIC_API_KEY is set, each news alert is double-checked by Claude to confirm
it is a genuine bullish endorsement / upgrade before it reaches Telegram, which
cuts false positives. Without a key, every keyword match is kept (fully free).
"""
import json

import requests

from bot import config


def llm_keep(alert):
    if not config.ANTHROPIC_API_KEY:
        return True

    prompt = (
        "You filter US-stock news alerts. Decide if the text below is a GENUINE "
        "bullish signal: an influential person endorsing/naming a company "
        "favorably, OR a clear analyst upgrade / raised price target. Ignore "
        "neutral coverage, lawsuits, or negative news. Reply with STRICT JSON only:\n"
        '{"keep": true|false, "ticker": "<best-guess ticker or empty>", "reason": "<short Chinese reason>"}\n\n'
        f"HEADLINE: {alert.get('title', '')}\nSUMMARY: {alert.get('detail', '')}"
    )
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": config.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": config.ANTHROPIC_MODEL,
                "max_tokens": 200,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        r.raise_for_status()
        text = r.json()["content"][0]["text"]
        verdict = json.loads(text[text.find("{"): text.rfind("}") + 1])
    except Exception as e:
        # On any failure, keep the alert — better a false positive than a miss.
        print(f"[filter] LLM check failed, keeping alert: {e}")
        return True

    if verdict.get("ticker") and not alert.get("tickers"):
        alert["tickers"] = [verdict["ticker"]]
    if verdict.get("reason"):
        alert["detail"] = f"{alert.get('detail', '')}\n\n🤖 {verdict['reason']}".strip()
    return bool(verdict.get("keep"))
