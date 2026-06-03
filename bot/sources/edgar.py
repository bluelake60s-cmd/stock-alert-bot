"""SEC EDGAR filings source.

Watches market-moving filers (config.SEC_FILERS) via the free EDGAR submissions
API. No key required; SEC only asks for a descriptive User-Agent.

Two kinds of alert:
  * 13D / 13G  — >5% stake, filed within ~10 days. The FAST, market-moving signal
    (e.g. Leopold Aschenbrenner's Nebius 13G). Sent as a quick link.
  * 13F-HR     — quarterly holdings (~45-day lag). The filing's information-table
    XML is parsed and diffed against the previous quarter, so the alert reads
    "🆕 新買 … ➕ 加注 … ➖ 減持 … ❌ 清倉 …" instead of just a link.
"""
import datetime
import xml.etree.ElementTree as ET

import requests

from bot import config

SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}"


def _headers():
    return {"User-Agent": config.SEC_USER_AGENT, "Accept-Encoding": "gzip, deflate"}


def _within(fdate, cutoff):
    try:
        return datetime.date.fromisoformat(fdate) >= cutoff
    except ValueError:
        return False


def _index_url(cik, accn):
    return f"{ARCHIVE.format(cik=int(cik), acc=accn.replace('-', ''))}/{accn}-index.htm"


def _desc(form):
    f = form.upper()
    if "13D" in f:
        return "🔵 持股超過 5% 披露（13D／主動持有，約 10 日內，較快、易郁市）— 入文件睇邊隻"
    if "13G" in f:
        return "🔵 持股超過 5% 披露（13G／被動持有，約 10 日內）— 入文件睇邊隻"
    return form


def _parse_infotable(xml_bytes):
    """Return {ISSUER_UPPER: [shares, value]} from a 13F information-table XML."""
    holdings = {}
    root = ET.fromstring(xml_bytes)
    for el in root.iter():
        if el.tag.split("}")[-1] != "infoTable":
            continue
        issuer, shares, value = None, 0.0, 0.0
        for c in el.iter():
            tag = c.tag.split("}")[-1]
            txt = (c.text or "").strip().replace(",", "")
            if tag == "nameOfIssuer":
                issuer = (c.text or "").strip()
            elif tag == "value":
                value = float(txt) if txt else 0.0
            elif tag == "sshPrnamt":
                shares = float(txt) if txt else 0.0
        if issuer:
            h = holdings.setdefault(issuer.upper(), [0.0, 0.0])
            h[0] += shares
            h[1] += value
    return holdings


def _summarize_13f(cik, accn, snapshots):
    """Parse the 13F info table, diff vs the stored snapshot, return a summary
    string (and update the snapshot). Returns None on fetch/parse failure so the
    caller can retry on the next run."""
    acc = accn.replace("-", "")
    base = ARCHIVE.format(cik=int(cik), acc=acc)
    try:
        items = requests.get(f"{base}/index.json", headers=_headers(), timeout=25).json()
        names = [it["name"] for it in items.get("directory", {}).get("item", [])]
        xmls = [n for n in names if n.lower().endswith(".xml") and n.lower() != "primary_doc.xml"]
        holdings = {}
        for nm in xmls:
            content = requests.get(f"{base}/{nm}", headers=_headers(), timeout=25).content
            parsed = _parse_infotable(content)
            if parsed:
                holdings = parsed
                break
    except Exception as e:
        print(f"[edgar] 13F parse failed ({accn}): {e}")
        return None
    if not holdings:
        return None

    cur = {k: v[0] for k, v in holdings.items()}
    prev = snapshots.get(cik)
    snapshots[cik] = cur  # new baseline for next quarter

    if not prev:
        top = sorted(holdings.items(), key=lambda kv: kv[1][1], reverse=True)[:10]
        lines = ["🟣 季度持倉 13F（首次記錄，主要持倉）："]
        lines += [f"• {iss.title()} — {int(v[0]):,} 股" for iss, v in top]
        return "\n".join(lines)

    new, added, reduced, sold = [], [], [], []
    for k in set(prev) | set(cur):
        p, c = prev.get(k, 0.0), cur.get(k, 0.0)
        if p == 0 and c > 0:
            new.append((k, c))
        elif c == 0 and p > 0:
            sold.append((k, p))
        elif c > p:
            added.append((k, c - p))
        elif c < p:
            reduced.append((k, p - c))

    def fmt(lst, n=6):
        picked = sorted(lst, key=lambda x: x[1], reverse=True)[:n]
        return "、".join(k.title() for k, _ in picked)

    parts = ["🟣 季度持倉 13F 變動："]
    if new:
        parts.append(f"🆕 新買：{fmt(new)}")
    if added:
        parts.append(f"➕ 加注：{fmt(added)}")
    if reduced:
        parts.append(f"➖ 減持：{fmt(reduced)}")
    if sold:
        parts.append(f"❌ 清倉：{fmt(sold)}")
    if len(parts) == 1:
        parts.append("（與上次記錄無變動）")
    return "\n".join(parts)


def _recent(cik, name):
    try:
        r = requests.get(SUBMISSIONS.format(cik=cik), headers=_headers(), timeout=25)
        r.raise_for_status()
        return r.json().get("filings", {}).get("recent", {})
    except Exception as e:
        print(f"[edgar] {name} fetch failed: {e}")
        return None


def fetch(state):
    alerts = []
    snapshots = state.setdefault("edgar_13f", {})
    done = state.setdefault("edgar_seen13f", [])
    done_set = set(done)
    cutoff = datetime.date.today() - datetime.timedelta(days=config.SEC_LOOKBACK_DAYS)
    forms_upper = {f.upper() for f in config.SEC_ALERT_FORMS}

    for cik, name in config.SEC_FILERS.items():
        recent = _recent(cik, name)
        if not recent:
            continue
        forms = recent.get("form", [])
        accns = recent.get("accessionNumber", [])
        dates = recent.get("filingDate", [])

        # Fast filings: 13D/13G within the lookback window.
        for i, form in enumerate(forms):
            fu = form.upper()
            if fu not in forms_upper or "13F" in fu:
                continue
            fdate = dates[i] if i < len(dates) else ""
            if not _within(fdate, cutoff):
                continue
            accn = accns[i]
            alerts.append({
                "id": f"edgar:{accn}",
                "kind": f"{name} 報 SEC 文件",
                "title": f"{form} · {fdate}",
                "detail": _desc(form),
                "url": _index_url(cik, accn),
                "tickers": [],
            })

        # 13F: parse the most-recent one once (updates the baseline snapshot;
        # only emits an alert if it is fresh enough to be within the window).
        idx = next((i for i, f in enumerate(forms) if f.upper().startswith("13F-HR")), None)
        if idx is None:
            continue
        accn, fdate = accns[idx], dates[idx]
        uid = f"edgar:{accn}"
        if uid in done_set:
            continue
        is_baseline = cik not in snapshots  # first time we see this filer
        detail = _summarize_13f(cik, accn, snapshots)
        if detail is None:
            continue  # transient failure — retry next run
        done.append(uid)
        done_set.add(uid)
        # Emit if the filing is fresh, or send a one-time current-holdings snapshot
        # the first time we ever record this filer.
        if _within(fdate, cutoff) or is_baseline:
            alerts.append({
                "id": uid,
                "kind": f"{name} 季度持倉（13F）",
                "title": f"13F-HR · {fdate}",
                "detail": detail,
                "url": _index_url(cik, accn),
                "tickers": [],
            })
    return alerts
