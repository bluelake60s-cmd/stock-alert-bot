import requests

from bot import config, translate


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def send(alert, dry_run=False):
    tickers = " ".join(f"${t}" for t in alert.get("tickers", []) if t)
    title = alert.get("title", "")
    zh = translate.to_zh(title)
    lines = [f"🚨 <b>{_esc(alert['kind'])}</b>", f"<b>{_esc(zh)}</b>"]
    if zh != title and title:
        lines.append(f"<i>{_esc(title)}</i>")  # keep the original headline for cross-check
    if tickers:
        lines.append(tickers)
    if alert.get("detail"):
        lines.append(_esc(alert["detail"]))
    if alert.get("url"):
        lines.append(alert["url"])
    text = "\n".join(lines)

    if dry_run:
        print(f"[DRY_RUN] would send:\n{text}\n")
        return True
    if not (config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID):
        print("[telegram] TELEGRAM_BOT_TOKEN/CHAT_ID missing; printing instead:\n" + text + "\n")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=20,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"[telegram] send failed: {e}")
        return False
