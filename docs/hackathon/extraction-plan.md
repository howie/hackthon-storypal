# StoryPal Hackathon 獨立專案抽取計畫

## Context

參加 Hackathon（規則要求 MM-DD-YY 期間新建專案）。目標是將 voice-lab 的「**適齡萬事通**」（Tutor Q&A）與「**語音故事**」（StoryPal）功能抽取為獨立可部署的 web app，放到 `../hackthon-storypal/`。新專案需要：
- 獨立運作（不依賴 voice-lab 其他模組）
- 獨立部署（Terraform + Docker + CI/CD）
- Git history 從零開始（符合 hackathon 新建規則）

---

## 功能範圍

### 保留
| 功能 | 說明 |
|------|------|
| **StoryPal 語音故事** | 模板選擇 → 兒童個人化設定 → LLM 故事生成 → TTS 語音合成 → 圖片生成 → 播放器 |
| **適齡萬事通 Tutor** | Q&A 問答、詞語接龍、即時語音互動 |
| **Google OAuth** | 登入認證（保留 `DISABLE_AUTH=true` 開發模式）|
| **Storage** | Local + GCS 雙模式 |

### 移除
TTS 比較、STT 測試、Multi-Role TTS 獨立頁面、Magic DJ、Music 獨立頁面、Voice Management、Provider Comparison、Quota Dashboard、Jobs 頁面、History 頁面、Advanced 頁面、Gemini Live Test 頁面、Credential Management 頁面

---

## 新專案結構

```
hackthon-storypal/
├── backend/
│   ├── src/
│   │   ├── main.py                          # 簡化版（移除 MusicJobWorker）
│   │   ├── config.py                        # 精簡設定
│   │   ├── audio_config.py                  # 原樣複製
│   │   ├── domain/
│   │   │   ├── errors.py
│   │   │   ├── entities/
│   │   │   │   ├── story.py                 # 原樣複製
│   │   │   │   ├── interaction_enums.py     # 原樣複製
│   │   │   │   ├── interaction_session.py   # 原樣複製
│   │   │   │   ├── interaction.py           # 原樣複製
│   │   │   │   ├── audio.py                 # AudioFormat enum（story tasks 需要）
│   │   │   │   └── tts.py                   # TTSRequest（story TTS 合成需要）
│   │   │   ├── repositories/
│   │   │   │   ├── story_repository.py      # 原樣複製
│   │   │   │   └── interaction_repository.py
│   │   │   └── services/
│   │   │       ├── story/                   # 全部原樣複製（engine, content_generator, templates, prompts, cost_calculator, tutor）
│   │   │       └── interaction/             # base, gemini_realtime, realtime_mode, latency_tracker
│   │   ├── application/
│   │   │   ├── interfaces/                  # llm_provider, tts_provider, image_provider, storage_service
│   │   │   └── tasks/
│   │   │       └── story_tasks.py           # 原樣複製
│   │   ├── infrastructure/
│   │   │   ├── auth/                        # jwt.py, domain_validator.py（原樣複製）
│   │   │   ├── persistence/
│   │   │   │   ├── database.py              # 原樣複製
│   │   │   │   ├── models.py                # ★ 重寫：只保留 User + Story* + Interaction* models
│   │   │   │   ├── story_repository_impl.py
│   │   │   │   ├── interaction_repository_impl.py
│   │   │   │   └── story_background_tasks.py
│   │   │   ├── providers/
│   │   │   │   ├── llm/                     # ★ 簡化：只保留 Gemini
│   │   │   │   ├── tts/                     # ★ 簡化：只保留 Gemini（Flash + Pro）
│   │   │   │   └── image/                   # Gemini Imagen
│   │   │   ├── storage/                     # local + GCS
│   │   │   ├── websocket/                   # base_handler + story/tutor/interaction handler
│   │   │   └── workers/
│   │   │       └── job_worker.py            # TTS 合成 worker（story 需要）
│   │   └── presentation/
│   │       └── api/
│   │           ├── __init__.py              # ★ 重寫：只註冊 story/tutor/auth/health routes
│   │           ├── dependencies.py          # ★ 重寫：簡化 Container
│   │           ├── middleware/              # auth, error_handler, rate_limit
│   │           ├── routes/
│   │           │   ├── health.py
│   │           │   ├── auth.py
│   │           │   ├── story.py
│   │           │   ├── story_ws.py
│   │           │   ├── tutor.py
│   │           │   └── tutor_ws.py
│   │           └── schemas/
│   │               └── story_schemas.py
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       └── 001_initial.py               # ★ 全新：單一 migration
│   ├── alembic.ini
│   ├── pyproject.toml                       # ★ 精簡依賴
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx                          # ★ 重寫：只有 storypal/tutor/auth routes
│   │   ├── components/
│   │   │   ├── auth/                        # ProtectedRoute, login
│   │   │   ├── layout/                      # ★ 重寫 Sidebar：只有 StoryPal + Tutor 導航
│   │   │   ├── shared/
│   │   │   ├── storypal/                    # 全部 18 個元件原樣複製
│   │   │   ├── tutor/
│   │   │   └── interaction/                 # tutor 需要的互動元件
│   │   ├── routes/
│   │   │   ├── auth/
│   │   │   ├── storypal/StoryPage.tsx
│   │   │   ├── story-game/StoryGamePage.tsx
│   │   │   └── tutor/TutorPage.tsx
│   │   ├── stores/                          # authStore, storypalStore, interactionStore, settingsStore
│   │   ├── services/                        # storypalApi, tutorApi, interactionApi
│   │   ├── types/                           # storypal, interaction
│   │   ├── hooks/
│   │   ├── lib/
│   │   └── config/
│   ├── package.json                         # ★ 精簡（移除 wavesurfer, dnd-kit 等）
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── index.html                           # 更新 title
│   ├── Dockerfile
│   └── nginx.conf
├── terraform/                               # ★ 簡化版
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── versions.tf
│   └── modules/
│       ├── cloud-run/                       # Backend + Frontend services
│       ├── cloud-sql/                       # PostgreSQL 16
│       ├── artifact-registry/
│       └── secrets/
├── docker-compose.yml                       # 只有 PostgreSQL（移除 Redis）
├── Makefile                                 # ★ 簡化
├── .github/workflows/
│   ├── ci.yml
│   └── cd.yml
├── CLAUDE.md
└── README.md                                # Hackathon 導向
```

---

## 關鍵重寫檔案

### 1. `backend/src/infrastructure/persistence/models.py`
只保留這些 models（約佔原檔 30%）：
- `UserModel` — OAuth 使用者
- `StoryTemplateModel` — 故事模板
- `StorySessionModel` — 故事 session（含 generation/synthesis/image status）
- `StoryTurnModel` — 故事段落（含 image_path, scene_description）
- `StoryGeneratedContentModel` — 歌曲/QA/互動選項
- `StoryCostEventModel` — 成本追蹤
- `InteractionSessionModel` — Tutor 即時互動 session
- `ConversationTurnModel` — 對話輪次
- `LatencyMetricsModel` — 延遲指標

### 2. `backend/src/presentation/api/dependencies.py`
簡化 Container：
- **保留**: `get_tts_providers()`（只有 Gemini）, `get_llm_providers()`（只有 Gemini）, `get_storage_service()`, `get_story_repository()`
- **移除**: 所有 STT providers, Azure TTS, VoAI, xGrok, GCP TTS, ElevenLabs, OpenAI LLM, Anthropic LLM, S3 storage, transcription repo, test record repo, voice repo, credential repo, compare use case 等

### 3. `backend/src/presentation/api/__init__.py`
只註冊 6 個 router：health, auth, story, story_ws, tutor, tutor_ws

### 4. `backend/src/main.py`
- 移除 `MusicJobWorker` import 和啟動
- 保留 `JobWorker`（story TTS 合成需要）
- 保留 story session 清理邏輯
- 移除 STT providers print

### 5. `frontend/src/App.tsx`
只保留 routes：`/`（新 Landing Page）, `/storypal`, `/story-game`, `/tutor`, `/login`, `/auth/callback`

### 6. `frontend/src/components/layout/Sidebar.tsx`
導航項目精簡為：首頁、語音故事、語音互動遊戲、適齡萬事通

### 7. `alembic/versions/001_initial.py`
全新 migration，建立上述 9 個 table + PostgreSQL enum types (`interaction_mode`, `session_status`) + seed 5 個預設故事模板

---

## 資料庫 Migration 策略

**不 copy voice-lab 的 31 個 migration 檔**。原因：
1. 包含大量無關 table（jobs, music, voices, transcriptions 等）
2. 有些 migration 之間有依賴關係和 merge 點
3. 新專案應有乾淨的 migration history

**策略**：建立單一 `001_initial.py`，參考 `models.py` 中的 table 定義，包含：
- 9 個 table 的 CREATE TABLE
- PostgreSQL ENUM types
- 所有 index 和 constraint
- Seed data：5 個預設故事模板（從 `templates.py` 的 `get_default_templates()` 取得）

---

## 依賴精簡

### Backend pyproject.toml

**保留**：
```
fastapi, uvicorn, pydantic, pydantic-settings, python-dotenv, python-multipart, websockets
sqlalchemy[asyncio], asyncpg, alembic
httpx, aiofiles
google-auth, PyJWT, cachetools
pydub, static-ffmpeg
google-cloud-storage
Pillow
```

**移除**：
```
redis, pipecat-ai, google-cloud-speech, google-cloud-texttospeech
azure-cognitiveservices-speech, elevenlabs, anthropic, openai
aioboto3, structlog, greenlet
deepgram-sdk, assemblyai, speechmatics-python
```

### Frontend package.json

**移除**：`@dnd-kit/*`, `wavesurfer.js`, 其他只被移除頁面使用的套件

---

## 實作步驟

### Phase 1: 專案骨架（~1.5h）
1. 初始化 git repo，建立目錄結構
2. 建立 `pyproject.toml`（精簡版）、`package.json`（精簡版）
3. 建立 `docker-compose.yml`（只有 PostgreSQL）
4. 建立 `.env.example`
5. 建立 `Makefile`
6. 建立 `CLAUDE.md`

### Phase 2: Backend 核心基礎設施（~2h）
7. 複製 `config.py` 並精簡
8. 複製 `audio_config.py`
9. 複製 `infrastructure/persistence/database.py`
10. **重寫** `infrastructure/persistence/models.py`（只保留 9 個 model）
11. 建立 `alembic/` 設定 + `001_initial.py` migration
12. 複製 auth 基礎設施（jwt.py, domain_validator.py, auth middleware）
13. 複製 storage 基礎設施（local, GCS, factory）
14. 驗證 `alembic upgrade head` 正常

### Phase 3: Domain & Application 層（~1.5h）
15. 複製所有 story entities
16. 複製 interaction entities + enums
17. 複製 story_repository interface + implementation
18. 複製 interaction_repository interface + implementation
19. 複製 application interfaces（ILLMProvider, ITTSProvider, IImageProvider, IStorageService）
20. 複製 story_tasks.py, story_background_tasks.py
21. 複製 domain errors

### Phase 4: Providers（~1h）
22. 複製 Gemini LLM provider
23. 複製 Gemini TTS provider + TTS base class
24. 複製 Gemini Imagen provider
25. 簡化 provider factory files（只保留 Gemini）

### Phase 5: Presentation 層（~2h）
27. 複製 WebSocket handlers（base, story, tutor, interaction）
28. 複製 story routes, story_ws, tutor, tutor_ws
29. 複製 story_schemas
30. 複製 health 和 auth routes
31. **重寫** `dependencies.py`
32. **重寫** API `__init__.py`
33. 複製 error_handler, rate_limit middleware
34. **重寫** `main.py`
35. 複製 `job_worker.py`（story TTS 合成用）

### Phase 6: Backend 驗證（~0.5h）
36. `ruff format` + `ruff check` + `mypy`
37. 啟動 backend，驗證 health endpoint
38. 驗證 story template listing
39. 驗證 session creation

### Phase 7: Frontend（~2.5h）
40. 複製所有 storypal 元件（18 個）
41. 複製 tutor 元件
42. 複製 interaction 元件（tutor 需要的）
43. 複製 stores（authStore, storypalStore, interactionStore, settingsStore）
44. 複製 services（storypalApi, tutorApi, interactionApi）
45. 複製 types（storypal, interaction）
46. 複製 auth 元件
47. **重寫** layout 元件（Sidebar 精簡）
48. 複製 shared 元件
49. **重寫** `App.tsx`
50. 精簡 `lib/api.ts`
51. 複製 config, hooks, index.css
52. 更新 `index.html` title
53. `tsc --noEmit` + `eslint` 驗證

### Phase 8: 整合測試（~0.5h）
54. 同時啟動 frontend + backend
55. 測試 OAuth 登入
56. 測試故事模板瀏覽
57. 測試故事 session 建立和生成
58. 測試故事播放 + TTS 合成
59. 測試 Tutor Q&A

### Phase 9: 部署設定（~2h）
60. 複製並調整 Dockerfiles
61. 驗證 Docker build（`--platform linux/amd64`）
62. 建立簡化版 Terraform modules
63. 建立 GitHub Actions CI/CD
64. 部署到 GCP Cloud Run

### Phase 10: 收尾（~1h）
65. 撰寫 hackathon README.md
66. **新建 Landing Page**：簡單首頁，包含 StoryPal 和 Tutor 兩個入口卡片，適合 hackathon demo 展示
67. 最終 `make check`
68. Tag v1.0.0

---

## 驗證方式

### 本地驗證
```bash
# 1. 基礎設施啟動
docker compose up -d          # PostgreSQL
make db-migrate               # Alembic migration

# 2. Backend 驗證
make dev-back                 # 啟動 backend
curl localhost:8888/api/v1/health
curl localhost:8888/api/v1/story/templates   # 應回傳 5 個模板

# 3. Frontend 驗證
make dev-front                # 啟動 frontend
# 瀏覽 http://localhost:5173 → 應看到 StoryPal 首頁

# 4. 程式碼品質
make check                    # ruff + mypy + eslint + tsc 全部通過

# 5. 端到端流程
# 在 UI 上選擇模板 → 設定兒童年齡 → 生成故事 → 播放 → Tutor Q&A
```

### 部署驗證
```bash
# Docker build
docker build --platform linux/amd64 -f backend/Dockerfile -t storypal-backend .
docker build --platform linux/amd64 -f frontend/Dockerfile -t storypal-frontend .

# Terraform apply
cd terraform && terraform plan    # 確認資源清單合理
```

---

## 風險與注意事項

1. **Import 鏈斷裂**：複製檔案後可能有 import 指向未帶來的模組（如 `models.py` 中引用了不存在的 model）。策略：每個 phase 結束都跑 `mypy` 驗證。

2. **story_tasks.py 跨層耦合**：直接 import `QuotaExceededError` from infrastructure provider。需確保 Imagen provider 也被複製。

3. **storypalStore.ts 的 transitive imports**：可能引用 `settingsStore`，需確認不會拉進更多不需要的 store。

4. **Hackathon 合規**：Git history 必須從零開始。不要 `git clone voice-lab` 再刪檔案，而是全新 `git init`，手動複製檔案。

5. **環境變數精簡**：新專案只需 `GEMINI_API_KEY`、`DATABASE_URL`、`GOOGLE_OAUTH_CLIENT_ID/SECRET`、`STORAGE_TYPE`、`AUDIO_BUCKET`（可選）。比 voice-lab 的 20+ env vars 大幅減少。
