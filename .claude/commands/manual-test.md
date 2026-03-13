# Manual Test Environment

Start the backend server and frontend app for manual testing.

## Instructions

Execute the following steps in order:

### Step 1: Stop any existing processes

Kill any running backend or frontend processes:

```bash
# Kill existing uvicorn/python processes on port 8888
lsof -ti:8888 | xargs kill -9 2>/dev/null || true

# Kill any existing Vite dev server on port 5173
lsof -ti:5173 | xargs kill -9 2>/dev/null || true
```

### Step 2: Start the backend server

Start the FastAPI backend server in the background:

```bash
cd $(git rev-parse --show-toplevel)/backend && \
nohup uv run uvicorn src.main:app --host 0.0.0.0 --port 8888 --reload > /tmp/storypal_backend.log 2>&1 &
```

Wait and verify the server is running:

```bash
sleep 3 && curl -s http://localhost:8888/api/v1/health
```

Expected output: `{"status":"healthy",...}`

### Step 3: Start the frontend dev server

Start the React frontend in the background:

```bash
cd $(git rev-parse --show-toplevel)/frontend && \
nohup npm run dev > /tmp/storypal_frontend.log 2>&1 &
```

Wait and verify:

```bash
sleep 3 && curl -s http://localhost:5173 | head -5
```

### Step 4: Open in browser

```bash
open http://localhost:5173
```

## API Endpoints for Testing

### Health Check
```bash
curl -s http://localhost:8888/api/v1/health | jq
```

## Logs

- Backend logs: `tail -f /tmp/storypal_backend.log`
- Frontend logs: `tail -f /tmp/storypal_frontend.log`

## Cleanup

To stop everything:

```bash
# Stop backend
lsof -ti:8888 | xargs kill -9 2>/dev/null || true

# Stop frontend
lsof -ti:5173 | xargs kill -9 2>/dev/null || true
```

## Quick Start (All-in-one)

Run everything in one command:

```bash
# Cleanup
lsof -ti:8888 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

# Start backend
cd $(git rev-parse --show-toplevel)/backend && \
nohup uv run uvicorn src.main:app --host 0.0.0.0 --port 8888 --reload > /tmp/storypal_backend.log 2>&1 &

# Start frontend
cd $(git rev-parse --show-toplevel)/frontend && \
nohup npm run dev > /tmp/storypal_frontend.log 2>&1 &

# Wait and verify
sleep 4
echo "=== Backend Health ===" && curl -s http://localhost:8888/api/v1/health | jq
echo "=== Frontend ===" && curl -s -o /dev/null -w "%{http_code}" http://localhost:5173

# Open browser
open http://localhost:5173
```

## Verification Checklist

After both services are running:

- [ ] Backend health: `curl http://localhost:8888/api/v1/health` returns healthy
- [ ] Frontend loads: `http://localhost:5173` shows the UI
