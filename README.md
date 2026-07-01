# stock-alert-bot

當有影響力嘅人物／大行**正面點名或背書**美股，即刻 Telegram 通知你。

靈感：黃仁勳點名睇好 → 相關股份多日發酵。呢個 bot 唔係要同 HFT 鬥秒（散戶追唔到第一波），而係**快過你自己刷新聞、唔漏接**早期催化劑。

> ⚠️ 純資訊工具，**唔係投資建議**。落唔落單係你嘅判斷同風險。

## 監聽信號

| 信號 | 來源 | 狀態 | 速度 |
|---|---|---|---|
| 🟢 ARK 每日持倉變動（Cathie Wood 買／沽） | `arkfunds.io`（免費，免 key） | ✅ 運作中 | 每個美股交易日更新一次 |
| 📣 巨頭開金口（黃仁勳／馬斯克／Altman 等正面點名） | Finnhub 新聞（免費 key） | ✅ 運作中 | 分鐘級（受 cron 限制） |
| 🌏 巨頭開金口・全網中英（Computex/GTC 等現場事件，台媒最快） | Google News RSS（免費，免 key） | ✅ 運作中 | 分鐘級；同股同日只發最快一篇 |
| 🟩 輝達官方合作／投資新聞稿（供應商暴漲源頭） | NVIDIA newsroom RSS（免費，免 key） | ✅ 運作中 | 官方發布即捉到 |
| 🟦 Google／Alphabet 投資帶動（AI 開支 → 帶起 Broadcom 等） | Google News RSS（免費，免 key） | ✅ 運作中 | 分鐘級；附「受惠股」 |
| 📈 分析師／大行升評 | Finnhub 新聞（免費 key） | ✅ 運作中 | 分鐘級 |
| 📊 分析師調評・全網中英（睇住 watched tickers；捉精品機構如 Aletheia） | Google News RSS（免費，免 key） | ✅ 運作中 | 分鐘級；每股每日最多一則 |
| 🔵 大戶 SEC 文件（Leopold／巴菲特／Burry） | SEC EDGAR（免費，免 key） | ✅ 運作中 | 13D/13G 約 10 日；13F 約 45 日 |
| 🇺🇸 Trump Truth Social 提及個股 | trumpstruth.org RSS（免費，免 key） | ✅ 運作中 | 即時；只發提及公司/$cashtag 的貼文 |
| 🏛️ 國會議員交易（裴洛西等重點議員） | Google News RSS（免費，免 key） | ✅ 運作中 | 每位議員每日最多一則；跟財務揭露報導 |

- 監聽嘅人物名單喺 [`bot/config.py`](bot/config.py) 嘅 `WATCHED_PEOPLE`，大戶 SEC 名單喺 `SEC_FILERS`（CIK → 名），自己加減即可。
- SEC 源會解析 13F 季度持倉、同上季比較，直接報「🆕 新買／➕ 加注／➖ 減持／❌ 清倉」；13D/13G（持股超 5%）即時報快訊。
- 國會源跟 `CONGRESS_MEMBERS`（裴洛西等），有交易／財務揭露報導就通知；分析師調評源跟 `WATCHED_TICKERS` ＋ `BANKS`（已收錄高盛、大摩、小摩、Aletheia、KeyBanc、Morningstar、Zacks 等）。
- 英文標題會**自動翻譯成繁體中文**先推送（下面附返英文原文對照）；已經係中文嘅唔會重譯。唔想翻譯就 set `TRANSLATE_TO_ZH=0`。

## 設定（一次過）

1. **Telegram bot**：喺 Telegram 同 `@BotFather` 傾 → `/newbot` → 抄低 token。再向你個新 bot 發一句嘢，然後開 `https://api.telegram.org/bot<TOKEN>/getUpdates` 搵你嘅 `chat_id`。
2. **Finnhub key**：去 https://finnhub.io 免費註冊攞 key。
3. （可選）**Anthropic key**：set 咗就會用 Claude 幫手過濾假信號，減少嘈。唔 set 都照行，全免費。

### 本機測試

```bash
pip install -r requirements.txt
cp .env.example .env        # 填返上面啲 key
set -a && . ./.env && set +a
python -m bot.main --source ark --dry-run      # 淨係試 ARK（免 Finnhub key 都得）
python -m bot.main --source all --dry-run      # 試齊四類，只印唔發
```

### 上 GitHub Actions（免費跑）

1. push 上 GitHub（建議 public repo，Actions 分鐘免費）。
2. Settings → Secrets and variables → Actions，加 `TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`、`FINNHUB_API_KEY`（同可選嘅 `ANTHROPIC_API_KEY`）。
3. **首次先行 bootstrap**：Actions → 揀 workflow → Run workflow → `bootstrap = true`。呢步會把現有舊新聞標記為「已見」，唔會一開機就轟你幾十條舊嘢。
4. 之後靠排程自動行（見 [`.github/workflows/alert.yml`](.github/workflows/alert.yml)）。

> ⏱️ **想穩定 ~15 分鐘一次**：GitHub 內建 cron 受節流，實際可能隔數個鐘先行。解決法係用外部排程器（例如免費嘅 cron-job.org）定時打 workflow 嘅 `workflow_dispatch` API：
> - URL：`https://api.github.com/repos/<owner>/stock-alert-bot/actions/workflows/alert.yml/dispatches`
> - `POST`，body `{"ref":"main"}`，headers 帶 `Authorization: Bearer <PAT>`、`Accept: application/vnd.github+json`、`User-Agent: <任意>`
> - PAT 用 fine-grained、淨係俾呢個 repo、權限 **Actions: Read and write**。手動／API 觸發唔受節流。

## 運作原理

`輪詢來源 → 關鍵字過濾 → （可選）Claude 二次判斷 → 去重 → Telegram` —— 同 repost-bot 一樣，去重 state 存喺 [`state/alerts.json`](state/) 並 commit 返 repo。`--dry-run` 唔會推進 state。

## 已知限制

- **唔係即時**：GitHub 內建 cron 受節流（實際可隔數個鐘）。駁咗上面嘅外部觸發後，穩定 ~15 分鐘一次；想 30–60 秒級就要一部長開細機（Railway／Fly.io／屋企 Raspberry Pi）—— 架構照用，改個排程即可。
- **commit 較密**：每次跑可能 commit 一次 state。想靜啲就調疏觸發頻率（ARK 本身一日先更新一次）。
- **國會交易**：之前免費嘅 stock-watcher 數據庫已鎖（403），結構化 API 全部要收費。所以改用**免費 Google News**捉重點議員（裴洛西等）嘅交易報導 —— 見 [`bot/sources/congress.py`](bot/sources/congress.py)。抓唔到每位議員嘅每筆小交易，但高知名度嗰啲（媒體必報）捉到。
- **分析師調評（Google News 版）** 淨係捉 `WATCHED_TICKERS` 相關嘅調評，避免變成「高盛一日幾十條」嘅火力網；精品機構若只喺中文／亞洲媒體出現，`analyst`（Finnhub）可能漏，靠呢個 Google News 版補返。

## License

[MIT](LICENSE)
