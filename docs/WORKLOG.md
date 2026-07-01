# Worklog

Dated record of notable changes and the reasoning behind them. Code-level detail lives
in the git commit messages; this file captures the *why* and the operational context
that commits don't. Newest first.

## 2026-06-25 — Sources, dedup, translation, faster cadence

### Added `CLAUDE.md`
Project guide for future work: architecture, pipeline, sources registry, alert-dict
shape, conventions, key decisions.

### New source: `analyst_news` (Google News analyst calls)
- Searches Google News (EN + ZH) for rating / price-target calls, surfaces those that
  name a `WATCHED_TICKER`. Complements the Finnhub `analyst` source, which only sees
  Finnhub's US-English feed and misses boutique / Asia / Chinese-media calls
  (e.g. Aletheia's Micron $1,600 "nuclear" target).
- **Noise control:** gated on watched tickers (not a "Goldman issued 40 targets today"
  firehose) and capped at **one alert per ticker per day** (fastest report).
- Tags the research firm when the headline names one.

### `analyst` (Finnhub) — expanded firm list
Added research firms to `config.BANKS`: Aletheia, KeyBanc, Morningstar, Zacks, Baird,
Stifel, B.Riley, Cantor, Oppenheimer, Needham, Rosenblatt. Their rating/target calls now
qualify. Note: this source only sees Finnhub's feed — `analyst_news` is the wider net.

### `congress` — rebuilt on free Google News (was dormant)
- The structured congress APIs are all paid/403 (House/Senate Stock Watcher dead; FMP,
  Capitol Trace paid; Reddit blocks unauth). So instead of buying data, we catch
  disclosures via Google News (same pattern as Trump holdings news).
- Tracks notable members (`config.CONGRESS_MEMBERS`, e.g. Pelosi) by name; tags a watched
  ticker when named but fires regardless (the disclosure is the signal).
- **Noise control:** one alert per member per day.
- This catches the Pelosi Intel/Uber-calls story the old dormant FMP source missed.
- Removed the unused FMP config + workflow secret.

### Chinese translation of headlines (`bot/translate.py`)
- English headlines are translated to Traditional Chinese before sending (free, keyless
  Google Translate endpoint), with the original English kept below for cross-check.
- Best-effort: already-Chinese and code-only titles are skipped; any failure falls back
  to the original so delivery never breaks. Toggle with `TRANSLATE_TO_ZH` (default on).

### `gnews` — fixed duplicate alerts
- **Bug:** non-ticker news was deduped per-link, so the same story from many outlets — or
  re-reported the next day — sent repeatedly (e.g. Cathie Wood/Tesla from Barron's and
  MSN both fired, since TSLA isn't a watched ticker).
- **Fix:** non-ticker stories now collapse by a normalized headline fingerprint
  (date-independent) → one alert per story across outlets and days.

### Leopold Aschenbrenner coverage strengthened
- `GNEWS_PERSON_ONLY`: high-signal, low-volume people (Leopold) pass the gnews relevance
  gate on a name match alone (fund-performance/strategy news no longer filtered out).
- Added dedicated EN+ZH queries for him / the Situational Awareness fund.
- His SEC filings (13D/13G/13F) were already tracked via `edgar` (CIK 0002045724).
- His own X/Twitter posts are **not** ingested — no reliable free access (Twitter paywall).

### Trump Truth Social — tried broadening, reverted
- Briefly surfaced market/economy posts (not only ticker-naming ones), then reverted:
  too noisy. Back to tight gate (post must name a watched ticker or carry a $CASHTAG).

### Faster delivery: external trigger (~15 min)
- GitHub's scheduled runs are heavily throttled (observed 1.5–5 h gaps despite the
  */15 cron). Fix: an external scheduler pings the workflow's `workflow_dispatch` every
  15 min, which is not throttled.
- Setup specifics (token, service config) are personal infra — see the local-only notes,
  not committed here.

### Dedup design note
Two dedup granularities are now in use across the news sources:
- **`ticker:date`** — one event per ticker per day (gnews ticker alerts, analyst_news).
- **`member:date` / headline fingerprint** — for member/person or non-ticker news.
State persistence is healthy (state committed every run); duplicates were a keying bug,
not state loss.
