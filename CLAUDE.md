# CLAUDE.md

US-stock endorsement alert bot. Polls a handful of public sources every 15 minutes,
de-duplicates, optionally sanity-checks with Claude, and pushes alerts to Telegram.
Runs entirely on GitHub Actions' free tier — no server, no database.

## What it does

Surfaces tradeable signals about US stocks (especially the NVIDIA AI ecosystem):
influential people endorsing a stock, Cathie Wood / ARK trades, analyst upgrades,
NVIDIA newsroom investment PRs, SEC 13D/13G/13F filings, and Trump Truth Social
posts that name a ticker. Each hit becomes a Telegram message.

## Architecture

```
.github/workflows/alert.yml   cron (*/15 staggered) → run bot → commit state back to repo
bot/main.py                   orchestrator: load state → fetch sources → dedup → filter → send → save
bot/config.py                 ALL tunables: API keys, watched people, cue words, tickers, SEC filers
bot/state.py                  JSON load/save; caps "seen" at 8000 ids
bot/filter.py                 optional Claude (Haiku) false-positive filter
bot/telegram.py               HTML-formatted delivery
bot/sources/*.py              one module per data source; each exposes fetch(state) → [alert dict]
state/alerts.json             git-committed dedup state (THIS is the database)
```

### Pipeline (`bot/main.py:19`)
1. Load `state/alerts.json` into a `seen` set.
2. Call each registered source's `fetch(state)`; sources are isolated by try/except —
   one failing source never breaks the run.
3. De-dupe new alerts against `seen` and within the current batch.
4. For news alerts (those carrying a `_text` key), run the optional Claude filter
   (`bot/filter.py`). ARK/SEC factual events skip the filter and always pass.
5. Send via Telegram, mark each id seen.
6. Save state — **unless `--dry-run`** (dry-run must never advance state).

### Sources registry (`bot/main.py:6`)
`SOURCES` dict maps a CLI name → `fetch` function. To add a source: create
`bot/sources/<name>.py` with `fetch(state) -> list[dict]`, then register it here.

| name | module | source | key needed |
|------|--------|--------|-----------|
| `ark` | `ark.py` | arkfunds.io daily trades | none |
| `ceo` | `finnhub_news.py:fetch_ceo` | Finnhub news, watched-person mentions | Finnhub |
| `analyst` | `finnhub_news.py:fetch_analyst` | Finnhub news, upgrade + bank name | Finnhub |
| `gnews` | `google_news.py` | bilingual Google News RSS | none |
| `nvidia` | `nvidia.py` | NVIDIA newsroom RSS | none |
| `google` | `google.py` | Alphabet AI-capex news (shares dedup w/ gnews) | none |
| `trump` | `trump.py` | Truth Social RSS + holdings news | none |
| `sec` | `edgar.py` | SEC EDGAR 13D/13G/13F | none |
| `congress` | `congress.py` | FMP House+Senate disclosures; alerts on `WATCHED_TICKERS` hits. **DORMANT** — needs a **paid** FMP plan (free tier returns 402); skips cleanly when `FMP_API_KEY` unset | FMP (paid) |

### Alert dict shape
```python
{
    "id": "unique:string",        # dedup key — must be stable & unique
    "kind": "category",           # bold header in Telegram
    "title": "headline",
    "detail": "body (optional)",
    "url": "https://...",
    "tickers": ["NVDA", ...],     # optional
    "_text": "lowercased text",   # PRESENT ONLY on news alerts → opts into Claude filter
}
```

## Running

```bash
python -m bot.main --source ark --dry-run     # test one source, no send, no state write
python -m bot.main --source all --dry-run     # test everything
python -m bot.main --bootstrap                # run ONCE on setup: mark current items seen, send nothing
python -m bot.main                            # live run (used by CI)
```

`--dry-run` prints instead of sending and does not advance state. `--bootstrap`
prevents a flood of historical alerts on first deploy. Both also settable via env
(`DRY_RUN`) / workflow_dispatch inputs.

Python 3.11. Only runtime dependency is `requests` (see `requirements.txt`); everything
else is stdlib.

## Configuration

Secrets via env vars (locally: `.env` → see `.env.example`; in CI: GitHub Secrets):
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — required to actually deliver
- `FINNHUB_API_KEY` — required for `ceo`/`analyst` sources
- `FMP_API_KEY` — enables the `congress` source, but requires a **paid** FMP plan
  (the free tier returns 402 on the congressional endpoints). Source is **dormant**:
  leave this unset and `congress` skips cleanly. Free public congress feeds
  (House/Senate Stock Watcher) are all 403 as of 2026.
- `ANTHROPIC_API_KEY` — optional; enables the Claude filter

All non-secret tuning (watched people + aliases, positive/upgrade cue words in EN+ZH,
watched tickers, tracked SEC filer CIKs, lookback windows) lives in `bot/config.py`.
**Extend behavior by editing config, not source code, where possible.**

## Key decisions & conventions

- **State lives in git, not a DB.** `state/alerts.json` is committed back by the workflow
  after each run (mirrors the author's repost-bot convention). Self-contained and free,
  but high-frequency runs can race on the commit — the workflow uses a `concurrency` group
  plus a rebase-retry loop (`alert.yml:63`) to handle conflicts.
- **Loose keyword matching, tight optional filter.** Source cue rules are deliberately
  permissive so signals aren't missed; the optional Claude filter removes false positives.
  On filter API failure it keeps the alert ("better a false positive than a miss").
- **ASCII vs CJK matching.** Latin ticker aliases use word boundaries (`\bintel\b`) to avoid
  e.g. "intel" matching "intelligence"; CJK terms use substring match (no word boundaries).
  This guard is why the Trump source doesn't spam on "intelligence".
- **Event-level dedup for news.** Google News collapses many outlets covering one event to a
  single fastest alert, keyed by `(ticker, date)` and logged in `state["gnews_events"]`
  (capped). `google.py` shares this state with `google_news.py`.
- **NVIDIA newsroom gates on "real money" words** (invest/stake/acquire/billion/$) because
  the PR is the root cause of supplier pops; pure product announcements are filtered out.
- **SEC 13F diffing.** `edgar.py` parses the XML info table and diffs against the prior
  quarter snapshot in `state["edgar_13f"]`, emitting 🆕新買 / ➕加注 / ➖減持 / ❌清倉 rather
  than a raw holdings dump.
- **Cron offset to 5/20/35/50** because GitHub's scheduler is oversubscribed at `:00`.
- **No unit tests.** Verification is via `--dry-run` and per-source isolation. When changing
  a source, test it with `python -m bot.main --source <name> --dry-run`.
- **Style:** snake_case functions/vars, UPPER_CASE config constants, module-level docstrings
  explaining rationale, defensive try/except per source, minimal type hints.

## Output language

README and user-facing alert text are in Traditional Chinese (zh-TW); code/comments in English.
