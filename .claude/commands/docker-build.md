# Docker Build + Smoke Test

Build Docker image 並自動驗證，防止推送壞的 image。

## 參數

$ARGUMENTS — 必要：`backend` 或 `frontend`（或 `both`）

## Workflow

### Step 1: 決定 Build Target

- `backend` → `backend/Dockerfile`，tag `storypal-backend:local`
- `frontend` → `frontend/Dockerfile`，tag `storypal-frontend:local`
- `both` → 依序 build 兩個

### Step 2: Build Image

**強制** `--platform linux/amd64`（Mac M1/M2 預設 ARM，Cloud Run 需要 amd64）：

```bash
docker build --platform linux/amd64 -f <target>/Dockerfile -t <tag> .
```

如果 build 失敗 → **STOP**，分析 build log 找出原因。

### Step 3: Smoke Test

啟動 container 並驗證基本功能：

**Backend**:
```bash
docker run -d --name storypal-backend-test -p 8889:8888 \
  -e DATABASE_URL=sqlite:///tmp/test.db \
  -e ENVIRONMENT=test \
  storypal-backend:local

# 等待啟動
sleep 3

# Health check
curl -sf http://localhost:8889/api/v1/health || echo "HEALTH CHECK FAILED"

# 清理
docker stop storypal-backend-test && docker rm storypal-backend-test
```

**Frontend**:
```bash
docker run -d --name storypal-frontend-test -p 3001:80 storypal-frontend:local

sleep 2

# 確認 HTTP 回應
curl -sf -o /dev/null -w "%{http_code}" http://localhost:3001/ || echo "FRONTEND CHECK FAILED"

docker stop storypal-frontend-test && docker rm storypal-frontend-test
```

### Step 4: Build Report

輸出結果：

```
## Docker Build Report
- Target: backend / frontend / both
- Platform: linux/amd64
- Build: PASS / FAIL
- Smoke test: PASS / FAIL
- Image size: <size>
```

如果 **FAIL**：
- **禁止** push 或 deploy
- 執行 `docker logs <container>` 查看錯誤
- 分析原因並建議修復方案
