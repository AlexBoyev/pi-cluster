#!/usr/bin/env bash
set -euo pipefail

CONTROL_PLANE_USER="${CONTROL_PLANE_USER:-admin}"
CONTROL_PLANE_HOST="${CONTROL_PLANE_HOST:-10.100.102.10}"
REMOTE_DIR="${REMOTE_DIR:-/home/admin/pi-cluster}"
TARGET="$CONTROL_PLANE_USER@$CONTROL_PLANE_HOST"

echo "==> Syncing to $TARGET:$REMOTE_DIR"
ssh "$TARGET" "mkdir -p $REMOTE_DIR"
git archive HEAD | ssh "$TARGET" "cd $REMOTE_DIR && tar x"

echo "==> Starting services"
ssh "$TARGET" "cd $REMOTE_DIR && docker compose up -d --build"

echo "==> Running migrations"
ssh "$TARGET" "cd $REMOTE_DIR && docker compose exec backend alembic upgrade head"

echo "==> Done — backend at http://$CONTROL_PLANE_HOST:8000/docs"
