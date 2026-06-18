import os

# --- Telegram (required to actually notify) ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# --- Data source keys ---
# Free key from https://finnhub.io (powers the CEO-mention + analyst-upgrade sources)
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")

# Free key from https://financialmodelingprep.com (250 req/day) — powers the `congress` source.
FMP_API_KEY = os.environ.get("FMP_API_KEY", "")

# --- Optional LLM filter (cuts false positives). The bot is fully free WITHOUT it. ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

DRY_RUN = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")

# ARK funds to watch for daily trades (Cathie Wood publishes buys/sells daily).
ARK_FUNDS = [s.strip() for s in os.environ.get("ARK_FUNDS", "ARKK,ARKQ,ARKW,ARKG,ARKF").split(",") if s.strip()]

# Influential people whose POSITIVE mentions we care about.
# key = canonical name; value = aliases (incl. Chinese) matched case-insensitively in headlines.
WATCHED_PEOPLE = {
    "Jensen Huang": ["jensen huang", "黃仁勳", "黄仁勋", "nvidia ceo"],
    "Elon Musk": ["elon musk", "馬斯克", "马斯克"],
    "Sam Altman": ["sam altman", "奧特曼", "奥特曼", "openai ceo"],
    "Sundar Pichai": ["sundar pichai", "pichai", "皮查伊", "google ceo", "alphabet ceo"],
    "Leopold Aschenbrenner": ["aschenbrenner", "situational awareness", "態勢感知"],
    "Cathie Wood": ["cathie wood", "木頭姐", "木头姐", "ark invest"],
    "Lisa Su": ["lisa su", "蘇姿丰", "苏姿丰", "amd ceo"],
    "Warren Buffett": ["warren buffett", "巴菲特", "berkshire"],
    "Michael Burry": ["michael burry", "大空頭"],
    "Dan Ives": ["dan ives", "wedbush"],
    "Jim Cramer": ["jim cramer", "克瑞莫"],
}

# Positive-endorsement cue words (English + Chinese). One must appear for a CEO-mention alert.
POSITIVE_CUES = [
    "praise", "bullish", "endorse", "backs", "favorite", "favourite", "top pick",
    "loves", "recommend", "names", "highlight", "betting on", "doubles down",
    "看好", "點名", "点名", "唱好", "力撐", "力挺", "首選", "首选", "睇好", "加碼", "增持",
]

# Analyst-upgrade cue words.
UPGRADE_CUES = [
    "upgrade", "upgrades", "raises price target", "raised price target",
    "initiates buy", "outperform", "overweight", "buy rating", "price target to",
    "上調", "上调", "升評", "升评", "目標價", "目标价", "首予買入", "評級上調",
]

# --- Google News RSS (bilingual, fast for live keynote/Computex/GTC events) ---
# Locale presets: (hl, gl, ceid).
GOOGLE_NEWS_LOCALES = {
    "zh": ("zh-TW", "TW", "TW:zh-Hant"),
    "en": ("en-US", "US", "US:en"),
}
# (query, locale). Covers each big mover in both languages + NVIDIA investment events.
GOOGLE_NEWS_QUERIES = [
    ('"黃仁勳"', "zh"),
    ('"Jensen Huang"', "en"),
    ('"輝達" OR "輝達投資" OR "NVIDIA投資"', "zh"),
    ('NVIDIA invests OR stake OR backs OR partnership', "en"),
    ('"Cathie Wood" OR "木頭姐" OR "Aschenbrenner"', "en"),
    # Leopold Aschenbrenner / Situational Awareness fund — both languages + fund name.
    ('"Leopold Aschenbrenner" OR "Situational Awareness" fund OR hedge OR AI', "en"),
    ('"Aschenbrenner" OR "Situational Awareness" OR "態勢感知" OR "情境感知"', "zh"),
]

# People who are low-volume but high-signal: for these, a name match ALONE passes the
# gnews gate (no positive-cue / watched-ticker required), so fund-performance and
# strategy news about them isn't filtered out. Keep this list small.
GNEWS_PERSON_ONLY = {"Leopold Aschenbrenner"}
# Only consider headlines published within this many hours (bounds the initial load;
# dedupe-by-link handles the rest).
NEWS_LOOKBACK_HOURS = int(os.environ.get("NEWS_LOOKBACK_HOURS", "48"))

# Companies in the NVIDIA-endorsement ecosystem (name aliases → ticker). Presence in
# a headline makes it relevant, and tags the alert with $TICKER.
WATCHED_TICKERS = {
    "MRVL": ["marvell", "邁威爾"],
    "NOK": ["nokia", "諾基亞"],
    "INTC": ["intel", "英特爾"],
    "COHR": ["coherent"],
    "LITE": ["lumentum"],
    "CRWV": ["coreweave"],
    "NBIS": ["nebius"],
    "AVGO": ["broadcom", "博通"],
    "VRT": ["vertiv"],
    "TSM": ["tsmc", "台積電", "taiwan semi"],
    "MU": ["micron", "美光"],
    "AMD": ["advanced micro", "amd"],
    "ORCL": ["oracle", "甲骨文"],
    # NB: deliberately NOT including NVDA/輝達/黃仁勳 — the speaker's own company
    # appears in almost every story, so it must not count toward relevance. The
    # signal is when he names some OTHER company.
}

# Google / Alphabet as a market mover — its AI capex/orders lift suppliers (Broadcom
# popped 6% on the $80B raise). No clean PR feed, so we use targeted Google News.
GOOGLE_INVEST_QUERIES = [
    ("(Alphabet OR Google) (capex OR invests OR billion OR Broadcom OR TPU)", "en"),
    ("(谷歌 OR Alphabet) (資本開支 OR 投資 OR 訂單 OR 億美元)", "zh"),
]
GOOGLE_INVEST_CUES = [
    "capex", "invest", "billion", "raise", "spending", "fundrais", "order",
    "資本開支", "投資", "億美元", "訂單", "募資", "燒錢", "受益", "受惠",
]

# NVIDIA official newsroom — press releases are the SOURCE of supplier/partner pops
# (the $20B Marvell, $1B Nokia deals). Only "real money" releases pass the gate.
NVIDIA_NEWSROOM_RSS = "https://nvidianews.nvidia.com/releases.xml"
NVIDIA_MONEY_CUES = ["invest", "stake", "acquir", "billion", "$"]

# --- Trump / Truth Social ---
# Fastest free Trump signal = his own posts (trumpstruth.org mirrors Truth Social as
# real RSS; Truth Social itself blocks scraping). His feed is ~99% political, so we
# only surface posts that NAME a company or carry a $CASHTAG — high precision.
TRUMP_TRUTH_RSS = "https://trumpstruth.org/feed"
# Trump holdings/trades coverage. The OGE disclosure trackers (open-cabinet,
# trumpstrades, trumptracker) are JS apps with no stable free API and lag the same
# filings the media report — so we catch each new disclosure via news instead
# (robust + as fast). Same-day coverage collapses to the fastest single report.
TRUMP_NEWS_QUERIES = [
    ("(Trump OR 特朗普 OR 川普) (持倉 OR 加倉 OR 加持 OR 買入 OR 持股 OR 披露)", "zh"),
    ("Trump (portfolio OR holdings OR \"bought shares\" OR disclosure OR \"stock trades\")", "en"),
]
TRUMP_TICKERS = {
    "INTC": ["intel"],
    "AAPL": ["apple"],
    "NVDA": ["nvidia"],
    "AMD": ["advanced micro"],
    "MU": ["micron"],
    "DELL": ["dell"],
    "BA": ["boeing"],
    "TSLA": ["tesla"],
    "TSM": ["tsmc", "taiwan semiconductor"],
    "AVGO": ["broadcom"],
    "X": ["u.s. steel", "us steel", "nippon steel"],
    "COIN": ["coinbase"],
    "MSTR": ["microstrategy"],
    "DJT": ["truth social", "trump media"],
    "GM": ["general motors"],
    "F": ["ford motor"],
    "LMT": ["lockheed"],
    "MRVL": ["marvell"],
}

# SEC EDGAR filers to watch (CIK → display name). Their filings move markets.
SEC_FILERS = {
    "0002045724": "Leopold Aschenbrenner（Situational Awareness LP）",
    "0001067983": "Warren Buffett（Berkshire Hathaway）",
    "0001649339": "Michael Burry（Scion Asset Management）",
}

# Filing types worth alerting (others ignored).
#   13D / 13G  = >5% beneficial-ownership stake — filed within ~10 days, the FAST,
#                market-moving kind (e.g. Leopold's Nebius 13G).
#   13F-HR     = quarterly holdings snapshot — ~45-day lag, shows direction.
SEC_ALERT_FORMS = {
    "SCHEDULE 13D", "SCHEDULE 13D/A", "SCHEDULE 13G", "SCHEDULE 13G/A",
    "SC 13D", "SC 13D/A", "SC 13G", "SC 13G/A", "13F-HR", "13F-HR/A",
}

# Only alert filings within this many days, so adding the source doesn't dump years
# of old 13Fs. The bot runs every 15 min, so a short window never misses anything live.
SEC_LOOKBACK_DAYS = int(os.environ.get("SEC_LOOKBACK_DAYS", "14"))

# SEC requires a descriptive User-Agent with contact info on every request.
SEC_USER_AGENT = os.environ.get("SEC_USER_AGENT", "stock-alert-bot bluelake60s@gmail.com")

# --- Congressional trades (Financial Modeling Prep) ---
# Members of Congress must disclose stock trades within 45 days (STOCK Act). We scan
# the latest House + Senate disclosure feeds and alert when a trade names one of
# WATCHED_TICKERS. "Latest" feeds return newest-first, so a couple of pages per
# chamber cost only a few of the 250 free daily requests.
FMP_CONGRESS_ENDPOINTS = {
    "眾議院": "https://financialmodelingprep.com/stable/house-latest",
    "參議院": "https://financialmodelingprep.com/stable/senate-latest",
}
# Only alert disclosures filed within this many days (bounds the initial load; the bot
# runs often so a short window never misses a fresh filing). Dedup handles re-sends.
# Filings lag ~30-45 days, so this is a slow "direction" signal, not a fast one.
CONGRESS_LOOKBACK_DAYS = int(os.environ.get("CONGRESS_LOOKBACK_DAYS", "30"))
# Pages of the latest feed to scan per chamber (100 rows/page).
CONGRESS_MAX_PAGES = int(os.environ.get("CONGRESS_MAX_PAGES", "3"))

# Major banks/brokers — used to qualify analyst-upgrade headlines and cut noise.
BANKS = [
    "goldman", "morgan stanley", "jpmorgan", "j.p. morgan", "bofa",
    "bank of america", "citi", "citigroup", "barclays", "ubs", "wells fargo",
    "wedbush", "evercore", "mizuho", "piper sandler", "raymond james",
    "jefferies", "deutsche bank", "hsbc", "td cowen", "bernstein",
]
