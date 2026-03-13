# Safe Migration Workflow

安全的 Alembic migration 工作流程，包含 pre-check、review、和驗證步驟。

## Step 1: Pre-Check

```bash
cd backend
uv run alembic current
uv run alembic heads
uv run alembic branches
```

- `current` vs `heads` 不同？→ 有 pending migration，先 `make db-migrate` 再繼續
- 有 multiple heads？→ 先 `alembic merge heads -m "merge"` 解決衝突
- 都一致？→ 可以安全產生新 migration

## Step 2: 產生 Migration

```bash
cd backend && uv run alembic revision --autogenerate -m "<描述>"
```

向使用者確認 migration 描述。

## Step 3: Review 生成檔案（CRITICAL）

讀取生成的 migration 檔案，確認：

1. **upgrade()**: 是否正確反映 model 改動？
   - 新欄位的 type、nullable、default 是否正確？
   - Foreign key 關係是否正確？
   - Index 是否需要？
2. **downgrade()**: 是否能正確 rollback？
   - Drop column/table 順序是否正確（先 drop FK 再 drop table）？
3. **沒有意外改動**: autogenerate 有時會偵測到不相關的 diff

列出 review 結果，請使用者確認後再 apply。

## Step 4: Apply Migration

```bash
cd backend && uv run alembic upgrade head
```

## Step 5: 驗證

```bash
# 確認 DB 在最新 head
cd backend && uv run alembic current

# 跑受影響的測試
cd backend && PYTHONPATH=. uv run pytest tests/ -k "<相關測試>" -v
```

如果有 API endpoint 涉及新欄位，用 curl 測試實際回應。

## Step 6: Stage & Commit

Migration 檔案和 model 改動應該一起 commit：

```bash
git add backend/alembic/versions/<new-migration>.py
git add backend/src/domain/models/<changed-model>.py
# 其他相關檔案
git commit -m "feat(db): <描述 migration 內容>"
```

**重要**：migration 檔案和 model 改動分開 commit 會導致 CI 或其他開發者的環境壞掉。
