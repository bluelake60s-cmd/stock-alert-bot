import argparse

from bot import config, filter as filt, state as state_mod, telegram
from bot.sources import ark, congress, edgar, finnhub_news, google, google_news, nvidia, trump

SOURCES = {
    "ark": ark.fetch,                 # ARK daily buys/sells (Cathie Wood)
    "ceo": finnhub_news.fetch_ceo,    # influential person named favorably (Finnhub, EN)
    "gnews": google_news.fetch,       # bilingual live-event news (Google News RSS)
    "nvidia": nvidia.fetch,           # NVIDIA official newsroom (partner/investment PRs)
    "google": google.fetch,           # Google/Alphabet AI capex lifting suppliers
    "trump": trump.fetch,             # Trump Truth Social posts naming a stock
    "analyst": finnhub_news.fetch_analyst,  # analyst / bank upgrade
    "sec": edgar.fetch,               # SEC 13D/13G/13F (Leopold, Buffett, Burry)
    "congress": congress.fetch,       # placeholder (no free source right now)
}


def run(source, state_path, dry_run, bootstrap):
    st = state_mod.load(state_path)
    seen = set(st.get("seen", []))

    names = list(SOURCES) if source == "all" else [source]
    raw = []
    for name in names:
        try:
            raw.extend(SOURCES[name](st))
        except Exception as e:
            print(f"[{name}] source error: {e}")

    # De-dupe against history and within this batch.
    fresh, batch = [], set()
    for a in raw:
        if a["id"] in seen or a["id"] in batch:
            continue
        batch.add(a["id"])
        fresh.append(a)
    print(f"{len(raw)} raw → {len(fresh)} new")

    if bootstrap:
        seen.update(a["id"] for a in fresh)
        st["seen"] = list(seen)
        state_mod.save(state_path, st)
        print(f"bootstrap: recorded {len(fresh)} ids as seen, sent nothing")
        return

    sent = 0
    for a in fresh:
        # News alerts (have "_text") get the optional LLM sanity check; ARK trades
        # are factual and always pass through.
        if "_text" in a and not filt.llm_keep(a):
            seen.add(a["id"])  # mark seen so we don't re-evaluate next run
            continue
        if telegram.send(a, dry_run=dry_run):
            sent += 1
        seen.add(a["id"])

    # Mirror the repost-bot convention: dry-run must NOT advance state.
    if not dry_run:
        st["seen"] = list(seen)
        state_mod.save(state_path, st)
    print(f"sent {sent} alerts (dry_run={dry_run})")


def main():
    p = argparse.ArgumentParser(description="US-stock endorsement alerts → Telegram")
    p.add_argument("--source", default="all", choices=list(SOURCES) + ["all"])
    p.add_argument("--state", default="state/alerts.json")
    p.add_argument("--dry-run", action="store_true", help="don't send Telegram, don't advance state")
    p.add_argument("--bootstrap", action="store_true",
                   help="record current items as seen and send nothing (run once on first setup)")
    args = p.parse_args()
    run(args.source, args.state, args.dry_run or config.DRY_RUN, args.bootstrap)


if __name__ == "__main__":
    main()
