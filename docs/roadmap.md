# Pi-Cluster Roadmap

## Phase 0 — Foundation (current)

- [x] Repository structure and documentation
- [x] Docker Compose scaffold
- [x] Backend scaffold (FastAPI, SQLAlchemy, Alembic)
- [x] Frontend scaffold (React, TypeScript, Vite)
- [ ] Migrations applied and API responding

## Phase 1 — Cluster Inventory

- [ ] Node registration API
- [ ] Node listing API
- [ ] Seed initial cluster nodes
- [ ] Dashboard node list

## Phase 2 — Node Health

- [ ] SSH connectivity check
- [ ] CPU, memory, disk, uptime, temperature collection via SSH
- [ ] Node status tracking (ONLINE / OFFLINE / DEGRADED / UNKNOWN)
- [ ] Background health polling task
- [ ] Health API endpoint
- [ ] Dashboard health indicators

## Phase 3 — Prometheus and Grafana

- [ ] Backend exposes `/metrics` endpoint
- [ ] Prometheus scrape configuration
- [ ] Grafana datasource and initial dashboards

## Phase 4 — Authentication

- [ ] JWT-based login and token refresh
- [ ] Protected API routes
- [ ] Frontend auth flow

## Phase 5 — Orchestration

Not started. Planned after Phase 4 is complete.
