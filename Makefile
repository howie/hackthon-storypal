.PHONY: help install install-backend install-frontend dev dev-back dev-front build test lint format check clean manual-test manual-test-stop tf-validate tf-check tf-plan tf-apply db-setup db-create-user db-docker-up db-docker-down

# Colors for output
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RESET := \033[0m

help:
	@echo "$(CYAN)StoryPal - 開發指令$(RESET)"
	@echo ""
	@echo "$(GREEN)安裝指令:$(RESET)"
	@echo "  make install          - 安裝所有依賴（前後端）"
	@echo "  make install-backend  - 安裝後端依賴"
	@echo "  make install-frontend - 安裝前端依賴"
	@echo ""
	@echo "$(GREEN)服務管理:$(RESET)"
	@echo "  make services-start   - 啟動 PostgreSQL"
	@echo "  make services-stop    - 停止 PostgreSQL"
	@echo ""
	@echo "$(GREEN)開發指令:$(RESET)"
	@echo "  make dev              - 同時啟動前後端開發伺服器"
	@echo "  make dev-back         - 啟動後端 (port 8888)"
	@echo "  make dev-front        - 啟動前端 (port 5173)"
	@echo ""
	@echo "$(GREEN)測試指令:$(RESET)"
	@echo "  make test             - 執行所有測試"
	@echo "  make test-back        - 後端測試"
	@echo "  make test-front       - 前端測試"
	@echo ""
	@echo "$(GREEN)程式碼品質:$(RESET)"
	@echo "  make check            - 執行所有檢查（lint + typecheck）"
	@echo "  make format           - 格式化程式碼"
	@echo ""
	@echo "$(GREEN)資料庫:$(RESET)"
	@echo "  make db-setup         - 初始化資料庫（借用 voice-lab-postgres）"
	@echo "  make db-migrate       - 執行資料庫遷移"
	@echo "  make db-revision      - 建立新的資料庫遷移"
	@echo "  make db-docker-up     - 啟動 storypal 獨立 postgres（standalone 模式）"
	@echo "  make db-docker-down   - 停止 storypal postgres"
	@echo ""
	@echo "$(GREEN)Terraform:$(RESET)"
	@echo "  make tf-validate      - tflint + terraform validate"
	@echo "  make tf-check         - GCP pre-apply 狀態檢查"
	@echo "  make tf-plan          - 完整驗證 + terraform plan"
	@echo "  make tf-apply         - 完整驗證 + terraform apply"

# =============================================================================
# Installation
# =============================================================================

install: install-backend install-frontend
	@echo "$(GREEN)✓ 所有依賴安裝完成$(RESET)"

install-backend:
	@echo "$(CYAN)安裝後端依賴...$(RESET)"
	cd backend && uv sync --all-extras

install-frontend:
	@echo "$(CYAN)安裝前端依賴...$(RESET)"
	cd frontend && npm install

# =============================================================================
# Services Management
# =============================================================================

services-start:
	@echo "$(CYAN)啟動 PostgreSQL...$(RESET)"
	docker-compose up -d
	@sleep 3
	@echo "$(GREEN)✓ PostgreSQL 已啟動 (localhost:5432)$(RESET)"

services-stop:
	@echo "$(CYAN)停止服務...$(RESET)"
	docker-compose down
	@echo "$(GREEN)✓ 服務已停止$(RESET)"

services-restart: services-stop services-start

services-logs:
	docker-compose logs -f

# =============================================================================
# Development
# =============================================================================

dev:
	@echo "$(CYAN)啟動開發伺服器...$(RESET)"
	@make -j2 dev-back dev-front

dev-back:
	@echo "$(CYAN)啟動後端伺服器 (http://localhost:8888)...$(RESET)"
	cd backend && uv run uvicorn src.main:app --host 0.0.0.0 --port 8888 --reload

dev-front:
	@echo "$(CYAN)啟動前端伺服器 (http://localhost:5173)...$(RESET)"
	cd frontend && npm run dev

# =============================================================================
# Build
# =============================================================================

build:
	@echo "$(CYAN)建構前端...$(RESET)"
	cd frontend && npm run build

# =============================================================================
# Testing
# =============================================================================

test: test-back test-front
	@echo "$(GREEN)✓ 所有測試完成$(RESET)"

test-back:
	@echo "$(CYAN)執行後端測試...$(RESET)"
	cd backend && PYTHONPATH=. uv run pytest tests/ -q --tb=short

test-front:
	@echo "$(CYAN)執行前端測試...$(RESET)"
	cd frontend && npm run test

# =============================================================================
# Code Quality
# =============================================================================

lint: lint-back lint-front
	@echo "$(GREEN)✓ 程式碼檢查完成$(RESET)"

lint-back:
	@echo "$(CYAN)檢查後端程式碼...$(RESET)"
	cd backend && uv run ruff check .

lint-front:
	@echo "$(CYAN)檢查前端程式碼...$(RESET)"
	cd frontend && npm run lint

format: format-back format-front
	@echo "$(GREEN)✓ 程式碼格式化完成$(RESET)"

format-back:
	@echo "$(CYAN)格式化後端程式碼...$(RESET)"
	cd backend && uv run ruff format .
	cd backend && uv run ruff check --fix .

format-front:
	@echo "$(CYAN)格式化前端程式碼...$(RESET)"
	cd frontend && npm run lint:fix

check: lint format-check typecheck
	@echo "$(GREEN)✓ 所有檢查完成$(RESET)"

format-check:
	@echo "$(CYAN)檢查程式碼格式...$(RESET)"
	cd backend && uv run ruff format --check .

typecheck:
	@echo "$(CYAN)執行型別檢查...$(RESET)"
	cd backend && uv run mypy src
	cd frontend && npm run typecheck

# =============================================================================
# Database
# =============================================================================

db-setup: db-create-user db-migrate
	@echo "$(GREEN)✓ 資料庫初始化完成$(RESET)"

db-create-user:
	@echo "$(CYAN)在 voice-lab-postgres 建立 storypal 帳號與資料庫...$(RESET)"
	@printf 'CREATE USER storypal WITH PASSWORD '"'"'storypal_dev'"'"';\nCREATE DATABASE storypal_dev OWNER storypal;\nCREATE DATABASE storypal_test OWNER storypal;\nGRANT ALL PRIVILEGES ON DATABASE storypal_dev TO storypal;\nGRANT ALL PRIVILEGES ON DATABASE storypal_test TO storypal;\n' \
		| docker exec -i voice-lab-postgres psql -U voicelab postgres 2>/dev/null || true
	@echo "$(GREEN)✓ storypal user + DB ready$(RESET)"

db-docker-up:
	@echo "$(CYAN)啟動 storypal postgres...$(RESET)"
	docker compose up -d postgres
	@echo "$(GREEN)✓ postgres 啟動完成，接著執行 make db-migrate$(RESET)"

db-docker-down:
	@echo "$(CYAN)停止 storypal postgres...$(RESET)"
	docker compose down

db-migrate:
	@echo "$(CYAN)執行資料庫遷移...$(RESET)"
	cd backend && uv run alembic upgrade head

db-revision:
	@echo "$(CYAN)建立新的資料庫遷移...$(RESET)"
	@read -p "遷移描述: " msg; \
	cd backend && uv run alembic revision --autogenerate -m "$$msg"

# =============================================================================
# Cleanup
# =============================================================================

clean:
	@echo "$(CYAN)清除建構產物...$(RESET)"
	rm -rf backend/.pytest_cache
	rm -rf backend/.mypy_cache
	rm -rf backend/.ruff_cache
	rm -rf backend/htmlcov
	rm -rf backend/.coverage
	rm -rf frontend/dist
	rm -rf frontend/node_modules/.vite
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✓ 清除完成$(RESET)"

# =============================================================================
# Terraform
# =============================================================================

TF_DIR := terraform
TF_PROJECT_ID ?= $(shell cd $(TF_DIR) && terraform output -raw project_id 2>/dev/null || echo "")

tf-validate:
	@echo "$(CYAN)執行 Terraform 靜態分析...$(RESET)"
	cd $(TF_DIR) && terraform validate
	@if command -v tflint >/dev/null 2>&1; then \
		cd $(TF_DIR) && tflint --init && tflint; \
	else \
		echo "$(YELLOW)⚠ tflint 未安裝 — 跳過靜態分析（安裝: brew install tflint）$(RESET)"; \
	fi
	@echo "$(GREEN)✓ Terraform 驗證完成$(RESET)"

tf-check:
	@echo "$(CYAN)執行 GCP Pre-apply 檢查...$(RESET)"
	@if [ -z "$(TF_PROJECT_ID)" ]; then \
		echo "$(YELLOW)⚠ 無法取得 project_id — 請提供: make tf-check TF_PROJECT_ID=<project_id>$(RESET)"; \
		exit 1; \
	fi
	$(TF_DIR)/scripts/pre-apply-check.sh "$(TF_PROJECT_ID)"
	@echo "$(GREEN)✓ GCP Pre-apply 檢查完成$(RESET)"

tf-plan: tf-validate tf-check
	@echo "$(CYAN)執行 Terraform Plan...$(RESET)"
	cd $(TF_DIR) && terraform plan
	@echo "$(GREEN)✓ Terraform Plan 完成$(RESET)"

tf-apply: tf-plan
	@echo "$(CYAN)執行 Terraform Apply...$(RESET)"
	cd $(TF_DIR) && terraform apply
	@echo "$(GREEN)✓ Terraform Apply 完成$(RESET)"

# =============================================================================
# Manual Testing
# =============================================================================

manual-test: manual-test-stop
	@echo "$(CYAN)啟動手動測試環境...$(RESET)"
	@cd backend && nohup uv run uvicorn src.main:app --host 0.0.0.0 --port 8888 --reload > /tmp/storypal_backend.log 2>&1 &
	@cd frontend && nohup npm run dev > /tmp/storypal_frontend.log 2>&1 &
	@sleep 4
	@echo "$(GREEN)=== Backend Health ===$(RESET)"
	@curl -s http://localhost:8888/api/v1/health | head -100 || echo "Backend not responding"
	@echo ""
	@echo "$(GREEN)✓ 測試環境已啟動$(RESET)"
	@echo "  Backend:  http://localhost:8888"
	@echo "  Frontend: http://localhost:5173"
	@open http://localhost:5173

manual-test-stop:
	@echo "$(CYAN)停止測試環境...$(RESET)"
	@lsof -ti:8888 | xargs kill -9 2>/dev/null || true
	@lsof -ti:5173 | xargs kill -9 2>/dev/null || true
	@echo "$(GREEN)✓ 測試環境已停止$(RESET)"
