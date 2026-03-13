# Implement Plan

從現有 plan 直接開始實作。**不要再產 plan 或 analysis — 直接寫 code。**

## 參數

$ARGUMENTS — 可選：feature 名稱或 plan 路徑（例如 `021-grok-integration`）

## Workflow

### Step 1: 找到 Plan

依序尋找：
1. 如果 `$ARGUMENTS` 是檔案路徑 → 直接讀取
2. `docs/features/*$ARGUMENTS*/plan.md`
3. `.specify/state/current-feature.json` → 取得 feature ID → 找對應 plan
4. 找不到 → **STOP**，問使用者指定 plan 位置

### Step 2: 確認 Worktree + Branch

```bash
git rev-parse --show-toplevel
git branch --show-current
```

- 如果在主 repo（`<repo-root>`）→ **STOP**，提醒使用者先建立 worktree：
  ```
  建議先建立 worktree 進行 feature 開發：
  cd <repo-root>
  git worktree add <repo-root>-worktrees/<name> -b <branch> origin/main
  cd <repo-root>-worktrees/<name>
  bash scripts/setup-worktree.sh
  ```
- 如果在 worktree 中且在 `main` 上 → 建立 feature branch（從 plan 名稱推導）
- 如果在 worktree 中且在 feature branch 上 → 繼續

### Step 3: 靜默讀取 Plan

讀取以下檔案（**不回述內容給使用者**，直接內化）：
- `plan.md` — 整體架構
- `tasks.md`（如果存在）— 具體任務清單
- `contracts/` 目錄下所有檔案（如果存在）— API 介面定義

### Step 4: 開始實作

**規則**：
- 立刻開始寫 code，不要再產 plan 或 analysis
- 每改 3 個檔案跑一次 `make check`
- 每完成一個 phase/task 輸出一行進度摘要（例如：「✓ Phase 1: LLM provider 完成」）
- Task 間**不問「要繼續嗎？」** — 除非遇到歧義或需要使用者決定的設計選擇
- 遇到 `make check` 失敗 → 立刻修好再繼續

### Step 5: 完成摘要

所有 task 完成後，輸出：
- 修改/新增的檔案清單
- `make check` 最終結果
- 下一步建議（例如：「跑 `make test` 驗證」或「用 `/pr` 建立 PR」）
