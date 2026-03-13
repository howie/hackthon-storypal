# StoryPal Development Guidelines

## Tech Stack

- **Backend**: Python 3.11+, FastAPI 0.109+, SQLAlchemy 2.0+, Pydantic 2.0+, Alembic
- **Frontend**: TypeScript 5.3+, Vite, React 18+, Tailwind CSS, Zustand
- **Database**: PostgreSQL 16
- **Infrastructure**: Terraform 1.6+ (GCP), Docker
- **External APIs**: Gemini (LLM, TTS, Imagen, Live), httpx

Always use these frameworks — do not introduce alternatives.

## Project Structure

```text
backend/          # FastAPI app (src/, tests/, alembic/)
frontend/         # Vite + React app (src/, tests/)
terraform/        # IaC (GCP)
```

## Commands

```bash
make dev            # 啟動前後端開發伺服器
make check          # lint + format-check + typecheck（commit 前必跑）
make test           # 跑全部測試（backend + frontend）
make test-back      # 只跑後端測試
make test-front     # 只跑前端測試
make db-migrate     # 執行 Alembic migration
make db-revision    # 建立新 migration
make format         # 自動格式化（ruff + eslint）
make clean          # 清除建構產物
```

## Code Style

- Python 3.11+: `X | Y` 取代 `Union[X, Y]`，`from collections.abc import Sequence`
- 遵循 ruff 格式，import 分三組（stdlib / third-party / local）
- **Guard clause 優先**：用 early return / early raise 處理錯誤

## Development Workflow

### Before ANY Code Changes

1. Use Python 3.10+ type annotations: `X | Y` instead of `Union[X, Y]`
2. Import `Sequence` from `collections.abc` not `typing`
3. Follow ruff formatting rules

### Before EVERY commit

```bash
make check  # MUST pass completely
```

### New Python files

```bash
ruff format <file>  # Format immediately after creation
```

### Adding Dependencies

Add to `pyproject.toml` (backend) or `package.json` (frontend), NOT `pip install`.

## GCP Deployment

```bash
# Docker build MUST specify platform
docker build --platform linux/amd64 -f backend/Dockerfile -t <image> .
docker build --platform linux/amd64 -f frontend/Dockerfile -t <image> .
```

## Key Architecture

- **Clean Architecture**: Domain → Application → Infrastructure → Presentation
- **Only Gemini providers**: LLM, TTS, Imagen, Live — no Azure/OpenAI/ElevenLabs
- **Storage**: Local (dev) / GCS (prod)
- **Auth**: Google OAuth with `DISABLE_AUTH=true` for dev
