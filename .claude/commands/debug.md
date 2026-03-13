# Debug Production Issue

Structured debugging methodology for this project. Enforces root cause analysis before suggesting fixes.

## Phase 1: Triage — Understand the Error

Before touching any code:

1. Ask for (or parse from context): the **exact error message**, **affected endpoint/component**, **stack trace**, and **when it started**.
2. Identify the error category:
   - **5xx** → server-side (backend, DB, migration, config)
   - **4xx** → auth/permission/routing issue
   - **CORS** → proxy, Cloud Run cold start, or missing header
   - **Build/type error** → frontend config, Tailwind, i18n, or TSC issue

## Phase 2: Database / Migration Check (CHECK EARLY)

500 errors 最常見的 root cause 是 migration 沒跑。**在查 application code 之前先排除。**

```bash
cd backend
# 目前 DB 在哪個 revision？
uv run alembic current
# 最新 head 是哪個？
uv run alembic heads
# 兩者不同 → 先跑 make db-migrate
# 檢查 multiple heads
uv run alembic branches
```

**快速判斷**：
- `column "X" does not exist` → migration 未跑
- `relation "X" does not exist` → table 的 migration 未跑
- 本地正常、deploy 後 500 → CI/CD 沒跑 migration

## Phase 3: Config Shadowing Check

For proxy/networking/CORS/500 issues:

```bash
# Check for duplicate config files that may shadow each other
ls -la frontend/vite.config.*
ls -la backend/*.env* .env*

# Check recent changes that may have caused regression
git log --oneline -10
git diff HEAD~5 -- frontend/vite.config.ts backend/src/main.py
```

**Common shadow issues in this project:**
- `vite.config.js` shadowing `vite.config.ts`
- `.env.local` overriding `.env` (not visible in git diff)
- Docker/Cloud Run environment missing variables that work locally

## Phase 4: Infrastructure Consistency Check

For port changes, env var changes, or deployment issues:

```bash
# Check all locations where this value is configured
grep -r "PORT\|8000\|8888" backend/ frontend/ --include="*.py" --include="*.ts" --include="*.env*" Dockerfile* terraform/
```

Always verify these locations are consistent:
- `backend/src/main.py` or app config
- `frontend/vite.config.ts` (proxy target)
- `Dockerfile` and `docker-compose.yml`
- `terraform/` (Cloud Run env vars)
- OAuth redirect URIs (Google Cloud Console)

## Phase 5: Apply Fix

Only after identifying root cause:
1. Apply the **minimal** fix.
2. If it's a migration: write and run the Alembic migration.
3. If it's a config: update ALL locations (see Phase 3).

## Phase 6: Verify — User-Facing Behavior (CRITICAL)

**Do NOT declare success based on error code change alone.**
- A 401 replacing a 500 is NOT a fix.
- Verify the actual user-facing behavior works end-to-end.

```bash
# Run full test suite
make test

# Test the specific endpoint/behavior that was broken
curl -v http://localhost:8888/api/v1/<affected-endpoint>
```

Only report success after confirming the original problem is resolved.

## Phase 7: Prevent Recurrence

After fixing, note:
- What was the root cause?
- What check would have caught this earlier?
- Should a test be added to prevent regression?
