import os

# --- Telegram (required to actually notify) ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# --- Data source keys ---
# Free key from https://finnhub.io (powers the CEO-mention + analyst-upgrade sources)
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "")

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

# Major banks/brokers — used to qualify analyst-upgrade headlines and cut noise.
BANKS = [
    "goldman", "morgan stanley", "jpmorgan", "j.p. morgan", "bofa",
    "bank of america", "citi", "citigroup", "barclays", "ubs", "wells fargo",
    "wedbush", "evercore", "mizuho", "piper sandler", "raymond james",
    "jefferies", "deutsche bank", "hsbc", "td cowen", "bernstein",
]
