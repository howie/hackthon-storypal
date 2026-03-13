#!/usr/bin/env bash
# PreToolUse hook: 在 Bash 工具呼叫前檢查 git commit 安全性
# 只攔截 git commit 指令，其他指令直接放行

set -euo pipefail

# 讀取 stdin JSON 取得 tool input
INPUT=$(cat)

# 取得 command 欄位
COMMAND=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")

# 非 git commit 指令 → 直接放行
if ! echo "$COMMAND" | grep -qE '\bgit\s+commit\b'; then
  exit 0
fi

# --- 以下只在 git commit 時執行 ---

WARNINGS=""

# 檢查 1: 是否在 main/master branch 上 commit
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
  WARNINGS="${WARNINGS}WARNING: Committing on '$CURRENT_BRANCH' branch — should you be on a feature branch?\n"
fi

# 檢查 2: staged 檔案是否包含敏感檔案
STAGED_FILES=$(git diff --cached --name-only 2>/dev/null || echo "")
if echo "$STAGED_FILES" | grep -qE '\.(env|key|pem|credentials)$|credentials\.json|\.env\.|secrets'; then
  MATCHED=$(echo "$STAGED_FILES" | grep -E '\.(env|key|pem|credentials)$|credentials\.json|\.env\.|secrets')
  WARNINGS="${WARNINGS}WARNING: Staged files may contain secrets:\n${MATCHED}\n"
fi

# 檢查 3: staged 檔案是否包含 symlink（防止 backend/storage 事件重演）
for f in $STAGED_FILES; do
  if [ -L "$f" ] 2>/dev/null; then
    WARNINGS="${WARNINGS}WARNING: Staged file is a symlink: $f — symlinks should not be committed\n"
  fi
done

# 有 warning 時輸出（不阻止 commit，只是提醒）
if [ -n "$WARNINGS" ]; then
  echo -e "$WARNINGS"
fi

exit 0
