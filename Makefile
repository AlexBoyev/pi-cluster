# Cluster deployment (runs on control plane via SSH)
.PHONY: deploy
deploy:
	bash scripts/deploy.sh

# Control plane management (run from the control plane itself)
.PHONY: up down build logs migrate shell-backend shell-frontend
up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

migrate:
	docker compose exec backend alembic upgrade head

shell-backend:
	docker compose exec backend bash

shell-frontend:
	docker compose exec frontend sh

# Local development — tunnel cluster postgres and redis to localhost
.PHONY: tunnel
tunnel:
	ssh -N \
	  -L 5432:localhost:5432 \
	  -L 6379:localhost:6379 \
	  pi@10.100.102.10

# Local development — run backend and frontend natively
.PHONY: dev-backend dev-frontend
dev-backend:
	cd backend && uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

dev-frontend:
	cd frontend && npm run dev
