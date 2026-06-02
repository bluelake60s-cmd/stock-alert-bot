"""SEC EDGAR filings source.

Watches a small set of market-moving filers (config.SEC_FILERS) for new 13D/13G
(>5% stake — fast) and 13F-HR (quarterly holdings) filings via the free EDGAR
submissions API. No key required; SEC only asks for a descriptive User-Agent.

The 13D/13G filings are the ones that move stocks: Leopold Aschenbrenner's
Situational Awareness LP filed a SCHEDULE 13G for its Nebius stake, which surged.
"""
import datetime

import requests

from bot import config

SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"


def _desc(form):
    f = form.upper()
    if "13D" in f:
        return "🔵 持股超過 5% 披露（13D／主動持有，約 10 日內，較快、易郁市）— 入文件睇邊隻"
    if "13G" in f:
        return "🔵 持股超過 5% 披露（13G／被動持有，約 10 日內）— 入文件睇邊隻"
    if "13F" in f:
        return "🟣 季度持倉報告（13F，約 45 日延遲，睇整體方向）"
    return form


def fetch(state):
    alerts = []
    cutoff = datetime.date.today() - datetime.timedelta(days=config.SEC_LOOKBACK_DAYS)
    headers = {"User-Agent": config.SEC_USER_AGENT, "Accept-Encoding": "gzip, deflate"}
    forms_upper = {f.upper() for f in config.SEC_ALERT_FORMS}

    for cik, name in config.SEC_FILERS.items():
        try:
            r = requests.get(SUBMISSIONS.format(cik=cik), headers=headers, timeout=25)
            r.raise_for_status()
            recent = r.json().get("filings", {}).get("recent", {})
        except Exception as e:
            print(f"[edgar] {name} fetch failed: {e}")
            continue

        forms = recent.get("form", [])
        accns = recent.get("accessionNumber", [])
        dates = recent.get("filingDate", [])
        for i, form in enumerate(forms):
            if form.upper() not in forms_upper:
                continue
            fdate = dates[i] if i < len(dates) else ""
            try:
                if datetime.date.fromisoformat(fdate) < cutoff:
                    continue
            except ValueError:
                continue
            accn = accns[i]
            url = (
                f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                f"{accn.replace('-', '')}/{accn}-index.htm"
            )
            alerts.append({
                "id": f"edgar:{accn}",
                "kind": f"{name} 報 SEC 文件",
                "title": f"{form} · {fdate}",
                "detail": _desc(form),
                "url": url,
                "tickers": [],
            })
    return alerts
