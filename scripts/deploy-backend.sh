#!/bin/bash
# ─────────────────────────────────────────────────────────────
# deploy-backend.sh — Deploy backend Lambda functions via CDK
#
# What it does:
#   1. Builds CDK TypeScript
#   2. Builds Docker images for both Lambda functions
#   3. Pushes images to ECR
#   4. Updates Lambda functions via CloudFormation
#
# Usage:
#   ./scripts/deploy-backend.sh
# ─────────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo -e "${CYAN}──────────────────────────────────────${NC}"
echo -e "${CYAN}  Backend Deployment (Docker + CDK)${NC}"
echo -e "${CYAN}──────────────────────────────────────${NC}"
echo ""

# ── Preflight checks ──────────────────────────────────────────
echo -e "${YELLOW}Preflight checks...${NC}"

for cmd in aws cdk docker node npm; do
  if ! command -v "$cmd" &>/dev/null; then
    echo -e "${RED}ERROR: '$cmd' not found. Please install it first.${NC}"
    exit 1
  fi
done

if ! docker info &>/dev/null; then
  echo -e "${RED}ERROR: Docker daemon is not running. Start Docker Desktop first.${NC}"
  exit 1
fi

ACCOUNT=$(aws sts get-caller-identity --query 'Account' --output text 2>/dev/null) || {
  echo -e "${RED}ERROR: AWS credentials not configured. Run 'aws configure' first.${NC}"
  exit 1
}
REGION=$(aws configure get region 2>/dev/null || echo "us-west-1")

echo -e "  AWS Account: ${GREEN}${ACCOUNT}${NC}"
echo -e "  AWS Region:  ${GREEN}${REGION}${NC}"
echo ""

# ── Step 1: Build CDK TypeScript ──────────────────────────────
echo -e "${YELLOW}[1/3] Building CDK TypeScript...${NC}"
cd "$PROJECT_ROOT/infrastructure"
npm run build 2>&1 | tail -3
echo -e "${GREEN}  Done.${NC}"
echo ""

# ── Step 2: CDK Deploy BackendStack ──────────────────────────
echo -e "${YELLOW}[2/3] Deploying BackendStack (Docker build + ECR push + Lambda update)...${NC}"
echo -e "  This builds 2 Docker images and pushes them to ECR. May take 3-10 min."
echo ""
cdk deploy BackendStack --require-approval never 2>&1
echo ""
echo -e "${GREEN}  BackendStack deployed.${NC}"
echo ""

# ── Step 3: Verify ───────────────────────────────────────────
echo -e "${YELLOW}[3/3] Verifying deployment...${NC}"
API_URL=$(aws cloudformation describe-stacks \
  --stack-name BackendStack \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
  --output text 2>/dev/null || echo "unknown")
echo -e "  API URL: ${GREEN}${API_URL}${NC}"
echo ""

echo -e "${GREEN}──────────────────────────────────────${NC}"
echo -e "${GREEN}  Backend deployment complete!${NC}"
echo -e "${GREEN}──────────────────────────────────────${NC}"
