# Architecture Decisions

## 2026-08-28 — FastAPI for the backend

Chosen over Flask and Django REST Framework.

FastAPI provides native async support, automatic OpenAPI documentation, and first-class Pydantic integration. The cluster monitoring workload is I/O-bound (SSH, database, HTTP), which benefits from async throughout.

## 2026-08-28 — PostgreSQL for persistent state

Chosen over SQLite.

PostgreSQL supports concurrent async connections via asyncpg, proper transactions, and the reliability expected from a control plane. SQLite has no async driver and serialises all writes.

## 2026-08-28 — SSH for initial metrics collection

Chosen over deploying node_exporter immediately.

SSH avoids requiring changes to each Pi node at bootstrap. Node Exporter will replace SSH-based collection once Prometheus is fully integrated (Phase 3), per the monitoring architecture.

## 2026-08-28 — Layered architecture: API → Services → Repositories → Database

Business logic lives in services. Data access lives in repositories. HTTP concerns stay in routes.

This keeps services independently testable and prevents database queries from appearing in routes or business logic from appearing in repositories.

## 2026-08-28 — Vite for frontend build tooling

Chosen over Create React App.

CRA is unmaintained. Vite provides fast HMR, a minimal configuration surface, and first-class TypeScript support. The project uses TypeScript strict mode throughout.

## 2026-08-28 — pi-node1 as dedicated control plane

pi-node1 (10.100.102.10) runs the full platform stack (backend, postgres, redis, prometheus, grafana) via Docker Compose. The other three nodes are workers.

Keeping the control plane on a dedicated node avoids resource contention with scheduled workloads and gives a stable host for the database and monitoring stack. All four nodes have their own SSD, RAM, and CPU — pi-node1's resources are reserved for platform services.

## 2026-08-28 — rsync + SSH for deployment, no CI/CD at this stage

Code is developed locally and deployed to pi-node1 via `scripts/deploy.sh` (rsync + docker compose). A CI/CD pipeline is deferred until the platform is stable enough to justify it.

## 2026-08-28 — SSH tunnel for local development database access

Local development connects to the cluster's PostgreSQL and Redis over an SSH tunnel rather than running a local database. This ensures local behaviour matches production and avoids maintaining a separate local database setup.
