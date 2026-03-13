#!/usr/bin/env bash
# pre-apply-check.sh — 在 terraform apply 之前驗證 GCP 狀態
# 用法: ./pre-apply-check.sh <project_id> [region]
set -euo pipefail

# ── 參數 ────────────────────────────────────────────────────────────────────
PROJECT_ID="${1:?Usage: $0 <project_id> [region]}"
REGION="${2:-asia-east1}"
BACKEND_SA="storypal-backend@${PROJECT_ID}.iam.gserviceaccount.com"

# ── 顏色 ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

ERRORS=0

pass() { echo -e "${GREEN}  ✓ $1${NC}"; }
fail() { echo -e "${RED}  ✗ $1${NC}"; ERRORS=$((ERRORS + 1)); }
warn() { echo -e "${YELLOW}  ⚠ $1${NC}"; }
section() { echo -e "\n${CYAN}── $1 ──${NC}"; }

# ── 1. API 啟用檢查 ─────────────────────────────────────────────────────────
section "檢查必要 API 是否已啟用"

REQUIRED_APIS=(
  "run.googleapis.com"
  "sqladmin.googleapis.com"
  "secretmanager.googleapis.com"
  "artifactregistry.googleapis.com"
  "compute.googleapis.com"
  "iam.googleapis.com"
  "cloudresourcemanager.googleapis.com"
)

ENABLED_APIS=$(gcloud services list --project="${PROJECT_ID}" --enabled --format="value(config.name)" 2>/dev/null || echo "")

for api in "${REQUIRED_APIS[@]}"; do
  if echo "${ENABLED_APIS}" | grep -q "^${api}$"; then
    pass "${api}"
  else
    fail "${api} 未啟用 — 請執行: gcloud services enable ${api} --project=${PROJECT_ID}"
  fi
done

# ── 2. Org Policy 檢查 ──────────────────────────────────────────────────────
section "檢查 Org Policy（iam.allowedPolicyMemberDomains）"

ORG_POLICY=$(gcloud org-policies describe iam.allowedPolicyMemberDomains \
  --project="${PROJECT_ID}" --format=json 2>/dev/null || echo "")

if [ -z "${ORG_POLICY}" ]; then
  pass "無 iam.allowedPolicyMemberDomains 限制（允許 allUsers）"
else
  if echo "${ORG_POLICY}" | grep -q '"allValues": "ALLOW"'; then
    pass "Org policy 允許所有 member domains"
  else
    warn "iam.allowedPolicyMemberDomains 已設定 — 若使用 allUsers IAM，apply 可能失敗"
    warn "請確認 policy 允許 allUsers，或改用 IAP 驗證"
  fi
fi

# ── 3. Secret 存在性與 Version 檢查 ──────────────────────────────────────────
section "檢查 Secret Manager Secrets"

REQUIRED_SECRETS=(
  "JWT_SECRET_KEY"
  "GEMINI_API_KEY"
  "DATABASE_PASSWORD"
  "GOOGLE_OAUTH_CLIENT_ID"
  "GOOGLE_OAUTH_CLIENT_SECRET"
)

for secret in "${REQUIRED_SECRETS[@]}"; do
  SECRET_EXISTS=$(gcloud secrets describe "${secret}" \
    --project="${PROJECT_ID}" --format="value(name)" 2>/dev/null || echo "")

  if [ -z "${SECRET_EXISTS}" ]; then
    fail "Secret ${secret} 不存在 — 請先建立並加入 version"
    continue
  fi

  VERSION_COUNT=$(gcloud secrets versions list "${secret}" \
    --project="${PROJECT_ID}" --filter="state=ENABLED" \
    --format="value(name)" --limit=1 2>/dev/null || echo "")

  if [ -z "${VERSION_COUNT}" ]; then
    fail "Secret ${secret} 存在但沒有啟用的 version — 請執行: gcloud secrets versions add ${secret} --data-file=<file>"
  else
    pass "Secret ${secret} 有啟用的 version"
  fi
done

# ── 4. Service Account 權限檢查 ──────────────────────────────────────────────
section "檢查 Service Account 權限"

SA_EXISTS=$(gcloud iam service-accounts describe "${BACKEND_SA}" \
  --project="${PROJECT_ID}" --format="value(email)" 2>/dev/null || echo "")

if [ -z "${SA_EXISTS}" ]; then
  warn "Backend SA ${BACKEND_SA} 不存在（首次部署前為正常）"
else
  pass "Backend SA ${BACKEND_SA} 存在"

  # 檢查 secretAccessor 角色
  for secret in "${REQUIRED_SECRETS[@]}"; do
    HAS_ACCESS=$(gcloud secrets get-iam-policy "${secret}" \
      --project="${PROJECT_ID}" --format=json 2>/dev/null | \
      grep -c "serviceAccount:${BACKEND_SA}" || echo "0")

    if [ "${HAS_ACCESS}" -gt 0 ]; then
      pass "SA 有 ${secret} 的存取權限"
    else
      fail "SA 缺少 ${secret} 的 secretAccessor 權限"
    fi
  done
fi

# ── 5. Container Image 檢查 ─────────────────────────────────────────────────
section "檢查 Artifact Registry Container Images"

REPO_EXISTS=$(gcloud artifacts repositories describe storypal \
  --project="${PROJECT_ID}" --location="${REGION}" \
  --format="value(name)" 2>/dev/null || echo "")

if [ -z "${REPO_EXISTS}" ]; then
  warn "Artifact Registry repo 'storypal' 不存在（首次部署前為正常）"
else
  pass "Artifact Registry repo 'storypal' 存在"

  BACKEND_IMG=$(gcloud artifacts docker images list \
    "${REGION}-docker.pkg.dev/${PROJECT_ID}/storypal/backend" \
    --format="value(package)" --limit=1 2>/dev/null || echo "")

  FRONTEND_IMG=$(gcloud artifacts docker images list \
    "${REGION}-docker.pkg.dev/${PROJECT_ID}/storypal/frontend" \
    --format="value(package)" --limit=1 2>/dev/null || echo "")

  if [ -n "${BACKEND_IMG}" ]; then
    pass "Backend image 存在"
  else
    warn "Backend image 不存在 — 首次部署請先 push image 或使用 placeholder"
  fi

  if [ -n "${FRONTEND_IMG}" ]; then
    pass "Frontend image 存在"
  else
    warn "Frontend image 不存在 — 首次部署請先 push image 或使用 placeholder"
  fi
fi

# ── 結果 ─────────────────────────────────────────────────────────────────────
echo ""
if [ "${ERRORS}" -gt 0 ]; then
  echo -e "${RED}╔══════════════════════════════════════════╗${NC}"
  echo -e "${RED}║  Pre-apply 檢查失敗：${ERRORS} 個錯誤           ║${NC}"
  echo -e "${RED}║  請修正上述錯誤後再執行 terraform apply  ║${NC}"
  echo -e "${RED}╚══════════════════════════════════════════╝${NC}"
  exit 1
else
  echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║  Pre-apply 檢查全部通過！                ║${NC}"
  echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
  exit 0
fi
