#!/usr/bin/env bash
set -euo pipefail

CONTROL_PLANE_USER="${CONTROL_PLANE_USER:-pi}"
CONTROL_PLANE_HOST="${CONTROL_PLANE_HOST:-10.100.102.10}"
REMOTE_DIR="${REMOTE_DIR:-/home/pi/pi-cluster}"
TARGET="$CONTROL_PLANE_USER@$CONTROL_PLANE_HOST"

echo "==> Syncing to $TARGET:$REMOTE_DIR"
ssh "$TARGET" "mkdir -p $REMOTE_DIR"
rsync -az --delete \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='node_modules' \
  --exclude='.env' \
  --exclude='postgres-data' \
  --exclude='redis-data' \
  --exclude='prometheus-data' \
  --exclude='grafana-data' \
  . "$TARGET:$REMOTE_DIR/"

echo "==> Starting services"
ssh "$TARGET" "cd $REMOTE_DIR && docker compose up -d --build"

echo "==> Running migrations"
ssh "$TARGET" "cd $REMOTE_DIR && docker compose exec backend alembic upgrade head"

echo "==> Done — backend at http://$CONTROL_PLANE_HOST:8000/docs"
