# stock-alert-bot

當有影響力嘅人物／大行**正面點名或背書**美股，即刻 Telegram 通知你。

靈感：黃仁勳點名睇好 → 相關股份多日發酵。呢個 bot 唔係要同 HFT 鬥秒（散戶追唔到第一波），而係**快過你自己刷新聞、唔漏接**早期催化劑。

> ⚠️ 純資訊工具，**唔係投資建議**。落唔落單係你嘅判斷同風險。

## 監聽信號

| 信號 | 來源 | 狀態 | 速度 |
|---|---|---|---|
| 🟢 ARK 每日持倉變動（Cathie Wood 買／沽） | `arkfunds.io`（免費，免 key） | ✅ 運作中 | 每個美股交易日更新一次 |
| 📣 巨頭開金口（黃仁勳／馬斯克／Altman 等正面點名） | Finnhub 新聞（免費 key） | ✅ 運作中 | 分鐘級（受 cron 限制） |
| 📈 分析師／大行升評 | Finnhub 新聞（免費 key） | ✅ 運作中 | 分鐘級 |
| 🔵 大戶 SEC 文件（Leopold／巴菲特／Burry） | SEC EDGAR（免費，免 key） | ✅ 運作中 | 13D/13G 約 10 日；13F 約 45 日 |
| 🏛️ 國會議員交易 | — | ⏸️ 暫停（免費源已鎖，要付費 API） | 延遲數日 |

- 監聽嘅人物名單喺 [`bot/config.py`](bot/config.py) 嘅 `WATCHED_PEOPLE`，大戶 SEC 名單喺 `SEC_FILERS`（CIK → 名），自己加減即可。
- SEC 源會解析 13F 季度持倉、同上季比較，直接報「🆕 新買／➕ 加注／➖ 減持／❌ 清倉」；13D/13G（持股超 5%）即時報快訊。

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
4. 之後每 15 分鐘自動行（見 [`.github/workflows/alert.yml`](.github/workflows/alert.yml)）。

## 運作原理

`輪詢來源 → 關鍵字過濾 → （可選）Claude 二次判斷 → 去重 → Telegram` —— 同 repost-bot 一樣，去重 state 存喺 [`state/alerts.json`](state/) 並 commit 返 repo。`--dry-run` 唔會推進 state。

## 已知限制

- **唔係即時**：GitHub Actions cron 最快約 5 分鐘、實際常延遲 5–15 分鐘。想 30–60 秒級就要一部長開細機（Railway／Fly.io／屋企 Raspberry Pi）—— 架構照用，改個排程即可。
- **commit 較密**：每 15 分鐘可能 commit 一次 state。想靜啲就調疏 cron（ARK 本身一日先更新一次）。
- **國會交易**：之前免費嘅 stock-watcher 數據庫已鎖（403）。要做就駁 Quiver／FMP 等付費 API，喺 [`bot/sources/congress.py`](bot/sources/congress.py) 補返 `fetch()`。

## License

[MIT](LICENSE)
