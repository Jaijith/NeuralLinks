#!/bin/bash
# ─────────────────────────────────────────────────────────────
# deploy-frontend.sh — Build React app and deploy to S3/CloudFront
#
# What it does:
#   1. Builds the React app with craco (production env)
#   2. Uploads to S3 with proper cache headers
#   3. Invalidates CloudFront cache
#
# Usage:
#   ./scripts/deploy-frontend.sh
# ─────────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo -e "${CYAN}──────────────────────────────────────${NC}"
echo -e "${CYAN}  Frontend Deployment (S3 + CloudFront)${NC}"
echo -e "${CYAN}──────────────────────────────────────${NC}"
echo ""

# ── Preflight checks ──────────────────────────────────────────
echo -e "${YELLOW}Preflight checks...${NC}"

for cmd in aws node npm; do
  if ! command -v "$cmd" &>/dev/null; then
    echo -e "${RED}ERROR: '$cmd' not found. Please install it first.${NC}"
    exit 1
  fi
done

ACCOUNT=$(aws sts get-caller-identity --query 'Account' --output text 2>/dev/null) || {
  echo -e "${RED}ERROR: AWS credentials not configured. Run 'aws configure' first.${NC}"
  exit 1
}
REGION=$(aws configure get region 2>/dev/null || echo "us-west-1")

echo -e "  AWS Account: ${GREEN}${ACCOUNT}${NC}"
echo -e "  AWS Region:  ${GREEN}${REGION}${NC}"

# Fetch S3 bucket and CloudFront distribution ID from CloudFormation
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name FrontendStack \
  --query "Stacks[0].Outputs[?OutputKey=='FrontendBucketName'].OutputValue" \
  --output text 2>/dev/null) || {
  echo -e "${RED}ERROR: Could not get FrontendStack outputs. Is the stack deployed?${NC}"
  exit 1
}
DIST_ID=$(aws cloudformation describe-stacks \
  --stack-name FrontendStack \
  --query "Stacks[0].Outputs[?OutputKey=='DistributionId'].OutputValue" \
  --output text 2>/dev/null)

echo -e "  S3 Bucket:   ${GREEN}${BUCKET_NAME}${NC}"
echo -e "  CloudFront:  ${GREEN}${DIST_ID}${NC}"
echo ""

# ── Resolve backend API URL ───────────────────────────────────
API_URL=$(aws cloudformation describe-stacks \
  --stack-name BackendStack \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
  --output text 2>/dev/null || echo "")

if [ -z "$API_URL" ] || [ "$API_URL" = "None" ]; then
  API_URL="https://api.2ness.com"
  echo -e "  Backend URL: ${YELLOW}${API_URL} (fallback — could not read from CloudFormation)${NC}"
else
  echo -e "  Backend URL: ${GREEN}${API_URL} (from CloudFormation)${NC}"
fi
echo ""

# ── Step 1: Build ─────────────────────────────────────────────
echo -e "${YELLOW}[1/4] Building React app (production)...${NC}"
cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
  echo -e "  Installing dependencies first..."
  npm install --legacy-peer-deps 2>&1 | tail -3
fi

REACT_APP_BACKEND_URL="$API_URL" CI=true npm run build 2>&1 | tail -5
echo -e "${GREEN}  Build complete.${NC}"
echo ""

# Verify the backend URL is baked into the bundle
API_HOST=$(echo "$API_URL" | sed 's|https://||')
MATCH_COUNT=$(grep -rl "$API_HOST" build/static/js/*.js 2>/dev/null | wc -l | tr -d ' ')
if [ "$MATCH_COUNT" -gt 0 ]; then
  echo -e "  Backend URL: ${GREEN}${API_URL} (found in ${MATCH_COUNT} JS chunks)${NC}"
else
  echo -e "${RED}  ERROR: Backend URL (${API_HOST}) NOT found in any JS bundle!${NC}"
  echo -e "${RED}  Check that REACT_APP_BACKEND_URL is used in the frontend code.${NC}"
  exit 1
fi
echo ""

# ── Step 2: Upload static assets (long cache) ────────────────
echo -e "${YELLOW}[2/4] Uploading static assets to S3 (immutable cache)...${NC}"
aws s3 sync build/ "s3://${BUCKET_NAME}/" \
  --delete \
  --cache-control "public, max-age=31536000, immutable" \
  --exclude "index.html" \
  --exclude "*.json" \
  --exclude "sw.js" \
  --exclude "offline.html" \
  --exclude "manifest.webmanifest" \
  2>&1 | tail -5
echo -e "${GREEN}  Static assets uploaded.${NC}"
echo ""

# ── Step 3: Upload no-cache files ────────────────────────────
echo -e "${YELLOW}[3/4] Uploading dynamic files (no-cache)...${NC}"
for file in index.html sw.js manifest.webmanifest offline.html; do
  if [ -f "build/$file" ]; then
    aws s3 cp "build/$file" "s3://${BUCKET_NAME}/$file" \
      --cache-control "public, max-age=0, must-revalidate" \
      2>&1 | grep -v "^$" || true
  fi
done
echo -e "${GREEN}  Dynamic files uploaded.${NC}"
echo ""

# ── Step 4: Invalidate CloudFront ────────────────────────────
echo -e "${YELLOW}[4/4] Invalidating CloudFront cache...${NC}"
INVALIDATION_ID=$(aws cloudfront create-invalidation \
  --distribution-id "$DIST_ID" \
  --paths "/*" \
  --query 'Invalidation.Id' \
  --output text 2>&1)
echo -e "  Invalidation ID: ${GREEN}${INVALIDATION_ID}${NC}"
echo -e "  Propagation takes ~1-2 minutes."
echo ""

echo -e "${GREEN}──────────────────────────────────────${NC}"
echo -e "${GREEN}  Frontend deployment complete!${NC}"
echo -e "${GREEN}  Live at: https://2ness.com${NC}"
echo -e "${GREEN}──────────────────────────────────────${NC}"
