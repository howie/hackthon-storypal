# StoryPal

[English](README.md)

**為 3–8 歲兒童打造的 AI 互動故事與教學平台**

StoryPal 運用 Google Gemini 的多模態能力 — LLM、TTS、Imagen 與 Live API — 透過語音驅動的故事、互動遊戲和 AI 家教，創造引人入勝的個人化學習體驗。

## 主要功能

| 功能 | 說明 |
|------|------|
| **Voice Story** | AI 為孩子量身打造互動故事，搭配多角色配音與精美插圖 |
| **Voice Game** | 孩子在故事世界中做出選擇，體驗沉浸式互動冒險 |
| **AI Tutor** | AI 家教以適合兒童的方式回答各種好奇問題 |

## 技術架構

- **Backend** — Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic 2.0
- **Frontend** — TypeScript, React 18, Vite, Tailwind CSS, Zustand
- **Database** — PostgreSQL 16
- **AI** — Google Gemini (LLM, TTS, Imagen, Live API)
- **Infrastructure** — Terraform (GCP), Docker

## 系統需求

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- [uv](https://docs.astral.sh/uv/)（Python 套件管理工具）
- Google Gemini API Key

## 快速開始

```bash
# 1. Clone 專案
git clone https://github.com/howie/hackthon-storypal.git
cd hackthon-storypal

# 2. 設定環境變數
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 3. 在 backend/.env 中設定你的 Gemini API key
#    編輯 backend/.env 並替換：GEMINI_API_KEY=your-gemini-api-key

# 4. 安裝相依套件
make install

# 5. 啟動 PostgreSQL 並執行資料庫遷移
make services-start
make db-migrate

# 6. 啟動開發伺服器
make dev
```

開啟 **http://localhost:5173** — 首頁會顯示三大功能。

> **備註：** 開發環境預設停用身份驗證（`DISABLE_AUTH=true`），本機測試無需設定 Google OAuth。

## 功能使用方式

### Voice Story (`/storypal`)
1. 在首頁點擊 **Voice Story**
2. 選擇故事主題或輸入自訂提示
3. AI 會生成搭配插圖與多角色配音的故事
4. 隨著故事發展進行互動

### Voice Game (`/story-game`)
1. 在首頁點擊 **Voice Game**
2. AI 會呈現一個故事情境與選項
3. 做出決定來引導冒險方向
4. 根據你的選擇體驗不同的故事結局

### AI Tutor (`/tutor`)
1. 在首頁點擊 **AI Tutor**
2. 提出任何好奇的問題
3. AI 會以適合兒童、淺顯易懂的方式回答

## 架構概覽

本專案採用 **Clean Architecture**，分為四層：

```
backend/src/
├── domain/          # 實體、Repository 介面、領域服務
├── application/     # Use Cases、DTOs
├── infrastructure/  # Gemini providers、DB repos、儲存服務
└── presentation/    # FastAPI 路由、中介層
```

```
frontend/src/
├── routes/          # 頁面元件（storypal, story-game, tutor, magic-dj）
├── components/      # 共用 UI 元件
├── services/        # API 客戶端服務
├── stores/          # Zustand 狀態管理
├── hooks/           # 自訂 React hooks
├── i18n/            # 雙語支援（en / zh-TW）
└── types/           # TypeScript 型別定義
```

## 可用指令

| 指令 | 說明 |
|------|------|
| `make install` | 安裝所有相依套件（backend + frontend） |
| `make dev` | 啟動前後端開發伺服器（backend :8888, frontend :5173） |
| `make services-start` | 透過 Docker Compose 啟動 PostgreSQL |
| `make services-stop` | 停止 PostgreSQL |
| `make db-migrate` | 執行 Alembic 資料庫遷移 |
| `make test` | 執行所有測試（backend + frontend） |
| `make check` | Lint + 格式檢查 + 型別檢查 |
| `make format` | 自動格式化程式碼（ruff + eslint） |
| `make clean` | 清除建構產物 |

## 授權條款

Apache License 2.0 — 詳見 [LICENSE](LICENSE)。
