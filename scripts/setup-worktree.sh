#!/usr/bin/env bash
# setup-worktree.sh — 在 worktree 中初始化 gitignored 資源
#
# Usage:
#   cd /path/to/worktree
#   bash scripts/setup-worktree.sh [main-repo-path]
#
# 功能：
#   1. 從主 repo 複製 .env 檔案（backend/.env, backend/.env.test, frontend/.env）
#   2. 將 backend/storage symlink 到主 repo（多 worktree 共享 runtime 檔案）
#   3. 安裝依賴（make install）

set -euo pipefail

# --- 顏色 ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*" >&2; }

# --- 偵測路徑 ---
WORKTREE_DIR="$(pwd)"
MAIN_REPO="${1:-$(git worktree list | head -1 | awk '{print $1}')}"

# 驗證我們在 worktree 中
if [[ ! -f "$WORKTREE_DIR/Makefile" ]]; then
    error "請在 worktree 根目錄執行此腳本"
    exit 1
fi

if [[ "$WORKTREE_DIR" == "$MAIN_REPO" ]]; then
    error "此腳本不應在主 repo 中執行"
    exit 1
fi

if [[ ! -d "$MAIN_REPO" ]]; then
    error "主 repo 不存在: $MAIN_REPO"
    exit 1
fi

echo "================================================"
echo "  Worktree 初始化"
echo "  worktree: $WORKTREE_DIR"
echo "  main repo: $MAIN_REPO"
echo "================================================"
echo

# --- 1. 複製 .env 檔案 ---
ENV_FILES=(
    "backend/.env"
    "backend/.env.test"
    "frontend/.env"
)

copied=0
for env_file in "${ENV_FILES[@]}"; do
    src="$MAIN_REPO/$env_file"
    dst="$WORKTREE_DIR/$env_file"
    if [[ -f "$src" ]]; then
        if [[ -f "$dst" ]]; then
            warn "$env_file 已存在，跳過（如需覆蓋請手動複製）"
        else
            cp "$src" "$dst"
            info "已複製 $env_file"
            ((copied++))
        fi
    else
        warn "$env_file 在主 repo 中不存在，跳過"
    fi
done

echo

# --- 2. Symlink backend/storage ---
MAIN_STORAGE="$MAIN_REPO/backend/storage"
WT_STORAGE="$WORKTREE_DIR/backend/storage"

if [[ -L "$WT_STORAGE" ]]; then
    # 已經是 symlink
    target="$(readlink "$WT_STORAGE")"
    if [[ "$target" == "$MAIN_STORAGE" ]]; then
        info "backend/storage 已是正確的 symlink"
    else
        warn "backend/storage 是 symlink 但指向 $target（預期 $MAIN_STORAGE）"
    fi
elif [[ -d "$WT_STORAGE" ]]; then
    # 是實際目錄 — 需要合併到主 repo 再 symlink
    warn "backend/storage 是實際目錄，正在合併到主 repo..."

    # 確保主 repo storage 目錄存在
    mkdir -p "$MAIN_STORAGE"

    # 用 rsync 合併（不覆蓋已存在的檔案）
    rsync -a --ignore-existing "$WT_STORAGE/" "$MAIN_STORAGE/"
    info "已合併 worktree 的 storage 內容到主 repo"

    # 移除 worktree 的 storage 目錄
    rm -rf "$WT_STORAGE"
    info "已移除 worktree 的 storage 目錄"

    # 建立 symlink
    ln -s "$MAIN_STORAGE" "$WT_STORAGE"
    info "已建立 symlink: backend/storage → $MAIN_STORAGE"
else
    # 不存在 — 直接建 symlink
    if [[ -d "$MAIN_STORAGE" ]]; then
        ln -s "$MAIN_STORAGE" "$WT_STORAGE"
        info "已建立 symlink: backend/storage → $MAIN_STORAGE"
    else
        warn "主 repo 的 backend/storage 不存在，跳過 symlink"
    fi
fi

echo

# --- 3. 安裝依賴 ---
echo "正在安裝依賴..."
if make install 2>&1; then
    info "依賴安裝完成"
else
    warn "make install 失敗，請手動執行"
fi

echo

# --- 摘要 ---
echo "================================================"
echo "  初始化完成"
echo "================================================"
echo
echo "  .env 檔案: 複製了 $copied 個"
if [[ -L "$WT_STORAGE" ]]; then
    echo "  storage:    $(readlink "$WT_STORAGE") (symlink)"
else
    echo "  storage:    ⚠️  未建立 symlink"
fi
echo
echo "  下一步: make dev"
echo "================================================"
