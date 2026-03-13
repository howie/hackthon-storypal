# New Job — 開啟新工作前準備（Worktree-First）

開始新 feature 或 fix 之前，執行此結構化流程確保環境乾淨並建立隔離工作空間。

**常數定義**（整個流程中使用絕對路徑）：
- `MAIN_REPO=/Users/howie/Workspace/github/hackthon-storypal`
- `WORKTREE_BASE=/Users/howie/Workspace/github/hackthon-storypal-worktrees`

## Step 1: 環境偵測

```bash
git rev-parse --show-toplevel
git status --short
```

**判斷邏輯**：

1. **已在 worktree**（`--show-toplevel` 路徑在 `WORKTREE_BASE` 下）：
   - 告知使用者「偵測到已在 worktree 中」
   - 跳過 Step 2 和 Step 4，直接執行 Step 3（Baseline Checks）→ Step 5（Report）
   - 不需要再問工作類型

2. **在主 repo 或其他位置**：
   - 檢查 uncommitted changes，有的話**警告**（提醒 stash 或 commit）
   - 用 `AskUserQuestion` 問工作類型：
     - **Worktree（推薦）** — 多檔 feature/fix，完全隔離。自動建立 worktree 並執行初始化
     - **Feature branch** — 單一小改動，快速 `git checkout -b feat/xxx`

   如果選 **Feature branch**：
   - `git checkout -b feat/<name>` 建立分支
   - 執行 Step 3 → Step 5，結束（跳過 Step 2、Step 4）

## Step 2: 建立 Worktree

根據使用者描述推導 branch 和 worktree 名稱（簡短有意義，例如 `fix-audio-leak`、`feat-dark-mode`）。

```bash
# 確保 main 是最新的
git -C /Users/howie/Workspace/github/hackthon-storypal fetch origin main

# 建立 worktree + branch
git -C /Users/howie/Workspace/github/hackthon-storypal worktree add /Users/howie/Workspace/github/hackthon-storypal-worktrees/<name> -b <name> origin/main
```

**注意**：使用 `git -C $MAIN_REPO` 確保在主 repo 執行，不依賴 Bash `cd` 持久性。

## Step 3: Baseline Checks

在目標工作目錄中執行（worktree 路徑或當前 repo），使用絕對路徑：

### 3a. 同步依賴

確保 `.venv` 和 `node_modules` 與最新 `pyproject.toml` / `package.json` 一致。
即使是既有 worktree，pull/rebase 後可能帶入新依賴，不先 sync 會導致 `make check` 因 import error 失敗。

```bash
cd <工作目錄>/backend && uv sync --all-extras
cd <工作目錄>/frontend && npm install
```

### 3b. make check

```bash
make -C <工作目錄> check
```

### 3c. Alembic migration 狀態

```bash
cd <工作目錄>/backend && uv run alembic current && uv run alembic heads
```

- `make check` 失敗是 **warning** 不是 blocker（使用者可能正要修 broken main）
- `alembic current` ≠ `alembic heads` 表示有 pending migration，報告但不阻擋

## Step 4: 執行 setup-worktree.sh

只在 Step 2 建立了新 worktree 時執行：

```bash
cd /Users/howie/Workspace/github/hackthon-storypal-worktrees/<name> && bash scripts/setup-worktree.sh /Users/howie/Workspace/github/hackthon-storypal
```

此腳本會：
1. 從主 repo 複製 `.env` 檔案
2. 將 `backend/storage` symlink 到主 repo（共享 runtime 檔案）
3. 執行 `make install` 安裝依賴

記錄 exit code，失敗時標記為 warning。

## Step 5: Go/No-Go Report

輸出結構化報告：

```
=== New Job Report ===
Mode:        🌳 Worktree / 🌿 Feature Branch
Branch:      <name>
Worktree:    /Users/howie/Workspace/github/hackthon-storypal-worktrees/<name>  （僅 worktree 模式）
make check:  ✅ passed / ⚠️ failed (N issues)
Migration:   ✅ at head / ⚠️ pending
Setup:       ✅ done / ⚠️ failed / ⏭️ skipped  （僅 worktree 模式）
─────────────────────────
Verdict:     ✅ GO
```

- 所有項目都是 info/warning，不會產生 NO-GO verdict
- 但會在 warning 項目旁列出修復建議

## Step 6: 引導切換（僅 Worktree 模式）

印出明確指令讓使用者切換到新 worktree：

```
📂 Worktree 已就緒！請在終端機執行：

   cd /Users/howie/Workspace/github/hackthon-storypal-worktrees/<name>

⚠️ 當前 Claude Code session 的工作目錄仍在原位置。
   建議在新目錄開啟新的 Claude Code session 以獲得正確的 cwd。
```
