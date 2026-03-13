#!/bin/bash
# Post-edit hook: quick lint check after Claude edits Python or TypeScript files.
# Claude Code pipes tool data as JSON to stdin.

set -euo pipefail

# Parse file_path from stdin JSON
FILE=$(python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('file_path', ''))
except Exception:
    print('')
" 2>/dev/null <<< "$(cat)" || echo '')

if [ -z "$FILE" ]; then
    exit 0
fi

# Python file in backend: run ruff check (fast, single-file)
if [[ "$FILE" == *.py && "$FILE" == *backend* ]]; then
    echo "🔍 ruff: $FILE"
    cd "$CLAUDE_PROJECT_DIR/backend"
    ruff check "$FILE" --quiet 2>&1 | head -15 || true
fi

# TypeScript/TSX file in frontend: run tsc (project-wide type check)
if [[ ("$FILE" == *.ts || "$FILE" == *.tsx) && "$FILE" == *frontend* ]]; then
    echo "🔍 tsc: $FILE"
    cd "$CLAUDE_PROJECT_DIR/frontend"
    npx tsc --noEmit 2>&1 | head -25 || true
fi
