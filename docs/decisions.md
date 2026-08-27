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
