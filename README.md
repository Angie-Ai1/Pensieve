# Pensieve — 個人每日數位足跡彙整 AI Agent

> 自動蒐集每日 YouTube 觀看紀錄與瀏覽文章，透過 AI 彙整分類後寫入 Obsidian 每日筆記；
> 後續將擴充為可互動討論學習規劃、新聞時事、工作任務的個人 AI Agent。

---

## 專案目標

現代人每天瀏覽大量網頁與影片，但內容容易看完即忘、難以回顧與延伸思考。
本專案的目標分兩階段：

- **Phase 1（MVP，開發中）**：每天自動彙整「我今天看了什麼」
  - 從瀏覽器歷史擷取當日 YouTube 觀看紀錄與瀏覽文章
  - 用 AI 分類、摘要、找出跨項目的觀察與洞察
  - 產出 Markdown 報告寫入 Obsidian vault
- **Phase 2（規劃中）**：互動式 AI Agent
  - 以每日彙整資料 + 歷史記錄作為 context
  - 與使用者討論學習規劃、新聞時事、工作任務、議題發想

---

## 技術棧

| 層次 | 技術 | 說明 |
|---|---|---|
| 自動化平台 | [n8n](https://n8n.io/)（Self-hosted, Docker） | Workflow 編排、排程、HTTP 呼叫 |
| 容器化 | Docker / Docker Compose | 單一 `n8n` 服務，含自訂 Dockerfile |
| 瀏覽器歷史查詢 | SQLite3 CLI | 讀取 Chrome / Edge `History` SQLite 資料庫 |
| YouTube metadata | YouTube Data API v3（`videos.list`） | 補全標題、頻道、分類、時長 |
| AI 彙整 | Google Gemini API（`gemini-2.5-flash`） | 分類、摘要、產生洞察（取代原規劃的 Claude API，成本考量） |
| 筆記輸出 | Obsidian Vault（本機 volume mount） | 每日 Markdown 報告 |
| 開發協作 | Claude Code | 跨對話維持開發脈絡與進度追蹤 |
| 依賴管理 | [Poetry](https://python-poetry.org/) | 為 Phase 2 互動式 Agent 預先建立 Python 環境骨架（目前尚無程式碼） |

---

## 架構總覽

```
┌──────────────────────────────────────────────────────────┐
│  Windows 主機                                              │
│                                                            │
│  Chrome/Edge History (唯讀)   Obsidian Vault (讀寫)        │
│         │                              ▲                  │
│         ▼                              │                  │
│  ┌──────────────────────────────────────────────────┐    │
│  │  n8n (Docker, restart: unless-stopped)            │    │
│  │                                                    │    │
│  │  讀取瀏覽器歷史 → 分類與排除 → videoId 去重        │    │
│  │       → YouTube videos.list（補 metadata）         │    │
│  │       → Gemini 彙整（分類/摘要/洞察）              │    │
│  │       → 整理輸出 → [待開發] 寫入 Obsidian Daily/   │    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

---

## 快速開始

### 前置需求

| 工具 | 用途 |
|---|---|
| Docker Desktop | 執行 n8n 容器，需設定 WSL2 backend 與 file sharing |
| Google Cloud Console 帳號 | 申請 YouTube Data API Key |
| Google AI Studio 帳號 | 申請 Gemini API Key |
| Obsidian | 檢視每日彙整報告（非必要，純檔案輸出） |

### 啟動步驟

```powershell
# 1. 複製環境變數範本並設定加密金鑰
cp .env.example .env
# 編輯 .env，填入 N8N_ENCRYPTION_KEY（建議用 openssl rand -hex 32 產生）

# 2. 建置並啟動 n8n（含 sqlite3 CLI 的客製化映像）
docker compose up -d --build

# 3. 開啟 n8n
# http://localhost:5678 → 完成 owner 帳號設定
```

接著在 n8n Web UI 設定 Credentials：

1. **Settings → Credentials → New → Query Auth**
   - `YouTube Data API`：Query Parameter 設為 `key`，Value 填入 YouTube Data API v3 Key
   - Gemini API：另建一組 Query Auth，Value 填入 Google AI Studio 申請的 API Key
2. 匯入 `workflows/02_youtube_metadata_summary.json`，並將上述兩組 credentials 綁定到對應的 HTTP Request 節點（`YouTube videos.list`、`Gemini 彙整`）

> ⚠️ `docker-compose.yml` 中的 volume 路徑（Chrome/Edge History、Obsidian vault）透過 `.env` 設定
>（範本見 `.env.example`），換機器或換使用者時只需更新 `.env`，不需修改 `docker-compose.yml`。

---

## 目前進度

Phase 1 MVP 開發中，瀏覽器歷史擷取、分類、YouTube metadata 補全與 Gemini 彙整已完成並測試成功；
尚待完成「YouTube 音樂內容排除」與「輸出 Markdown + 排程/補跑邏輯」。

---

## 授權

個人 Side Project，目前僅供自用，未設定公開授權條款。
