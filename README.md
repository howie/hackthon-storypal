# StoryPal

[繁體中文](README.zh-TW.md)

**AI-powered interactive storytelling and tutoring platform for children (ages 3–8)**

StoryPal uses Google Gemini's multimodal capabilities — LLM, TTS, Imagen, and Live API — to create engaging, personalized learning experiences through voice-driven stories, interactive games, and an AI tutor.

## Key Features

| Feature | Description |
|---------|-------------|
| **Voice Story** | AI crafts personalized interactive stories with multi-character voices and beautiful illustrations |
| **Voice Game** | Children make choices in the story world for an immersive interactive adventure |
| **AI Tutor** | AI tutor answers all kinds of curious questions in a child-friendly way |

## Tech Stack

- **Backend** — Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic 2.0
- **Frontend** — TypeScript, React 18, Vite, Tailwind CSS, Zustand
- **Database** — PostgreSQL 16
- **AI** — Google Gemini (LLM, TTS, Imagen, Live API)
- **Infrastructure** — Terraform (GCP), Docker

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Google Gemini API Key

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/howie/hackthon-storypal.git
cd hackthon-storypal

# 2. Set up environment variables
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 3. Set your Gemini API key in backend/.env
#    Edit backend/.env and replace: GEMINI_API_KEY=your-gemini-api-key

# 4. Install dependencies
make install

# 5. Start PostgreSQL & run migrations
make services-start
make db-migrate

# 6. Start dev servers
make dev
```

Open **http://localhost:5173** — the landing page shows all three features.

> **Note:** Auth is disabled by default (`DISABLE_AUTH=true`), so no Google OAuth setup is needed for local testing.

## How to Test Each Feature

### Voice Story (`/storypal`)
1. Click **Voice Story** on the landing page
2. Choose a story topic or enter a custom prompt
3. The AI generates a story with illustrations and multi-character voice narration
4. Interact with the story as it progresses

### Voice Game (`/story-game`)
1. Click **Voice Game** on the landing page
2. The AI presents a story scenario with choices
3. Make decisions to guide the adventure
4. Experience different story outcomes based on your choices

### AI Tutor (`/tutor`)
1. Click **AI Tutor** on the landing page
2. Ask any question a curious child might have
3. The AI responds in a child-friendly, age-appropriate way

## Architecture Overview

The project follows **Clean Architecture** with four layers:

```
backend/src/
├── domain/          # Entities, repository interfaces, domain services
├── application/     # Use cases, DTOs
├── infrastructure/  # Gemini providers, DB repos, storage
└── presentation/    # FastAPI routes, middleware
```

```
frontend/src/
├── routes/          # Page components (storypal, story-game, tutor, magic-dj)
├── components/      # Shared UI components
├── services/        # API client services
├── stores/          # Zustand state management
├── hooks/           # Custom React hooks
├── i18n/            # Bilingual support (en / zh-TW)
└── types/           # TypeScript type definitions
```

## Available Commands

| Command | Description |
|---------|-------------|
| `make install` | Install all dependencies (backend + frontend) |
| `make dev` | Start both dev servers (backend :8888, frontend :5173) |
| `make services-start` | Start PostgreSQL via Docker Compose |
| `make services-stop` | Stop PostgreSQL |
| `make db-migrate` | Run Alembic database migrations |
| `make test` | Run all tests (backend + frontend) |
| `make check` | Lint + format check + typecheck |
| `make format` | Auto-format code (ruff + eslint) |
| `make clean` | Clean build artifacts |

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.
