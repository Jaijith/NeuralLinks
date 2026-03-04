#!/bin/bash
# ─────────────────────────────────────────────────────────────
# deploy.sh — Deploy both backend and frontend
#
# For individual deployments, use:
#   ./scripts/deploy-backend.sh   (Docker + CDK → Lambda)
#   ./scripts/deploy-frontend.sh  (Build → S3 + CloudFront)
#
# Usage:
#   ./scripts/deploy.sh              # deploy both
#   ./scripts/deploy.sh backend      # backend only
#   ./scripts/deploy.sh frontend     # frontend only
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

case "${1:-all}" in
  backend)
    exec "$SCRIPT_DIR/deploy-backend.sh"
    ;;
  frontend)
    exec "$SCRIPT_DIR/deploy-frontend.sh"
    ;;
  all)
    echo ""
    echo "===== Deploying Backend ====="
    "$SCRIPT_DIR/deploy-backend.sh"
    echo ""
    echo "===== Deploying Frontend ====="
    "$SCRIPT_DIR/deploy-frontend.sh"
    ;;
  *)
    echo "Usage: $0 [backend|frontend|all]"
    exit 1
    ;;
esac
