# Pi-Cluster Roadmap

## Phase 0 — Foundation ✓
- [x] Repository structure and documentation
- [x] Docker Compose scaffold
- [x] Backend scaffold (FastAPI, SQLAlchemy, Alembic)
- [x] Frontend scaffold (React, TypeScript, Vite)
- [x] Migrations applied and API responding

## Phase 1 — Cluster Inventory ✓
- [x] Node registration API
- [x] Node listing API
- [x] Seed initial cluster nodes (pi-node1–4)
- [x] Dashboard node list

## Phase 2 — Node Health ✓
- [x] SSH connectivity check (paramiko)
- [x] CPU, memory, disk, uptime, temperature via SSH
- [x] Node status tracking (ONLINE / OFFLINE / DEGRADED / UNKNOWN)
- [x] Background health polling (30s interval, asyncio)
- [x] Health API endpoint with Redis cache (90s TTL)
- [x] Dashboard health cards with ring gauges

## Phase 3 — Observability ✓
- [x] Backend `/metrics` endpoint (prometheus-fastapi-instrumentator)
- [x] Custom Prometheus Gauges per node (CPU, RAM, disk, temp, uptime)
- [x] Prometheus scrape config
- [x] Grafana auto-provisioned datasource + dashboard
- [x] Light-blue admin UI with sidebar navigation

## Phase 4 — Authentication ✓
- [x] JWT-based login / token refresh
- [x] Protected API routes (FastAPI dependency)
- [x] Frontend auth flow (login page, token storage)
- [x] Role-based access (admin / viewer)

## Phase 5 — CI/CD Pipeline ✓
- [x] Jenkins deployed as Docker service on pi-node1 (:8080)
- [x] Jenkins pipeline for build → migrate → deploy → health check on git push
- [x] SCM polling every 2 minutes (triggers on any master push)
- [ ] Webhook from Git repo to Jenkins (optional, polling sufficient)
- [ ] Automated docker build and push to local registry

## Phase 6 — Kubernetes + GitOps ✓
- [x] K3s server on pi-node1, agents on pi-node2/3/4
- [x] ArgoCD deployed on K3s (:30443)
- [x] ArgoCD Application watching k8s/apps/ in this repo
- [x] Sample nginx workload deployed via GitOps
- [ ] Workload scheduling and placement policies

## Phase 7 — Orchestration ✓
- [x] Workload API (create / list / delete K8s deployments)
- [x] Kubernetes Python client integrating with K3s via kubeconfig
- [x] Capacity-aware placement (picks node with most free CPU)
- [x] Node cordon / uncordon via API and dashboard UI
- [x] Workloads page in frontend (deploy form, live table, capacity cards)

## Phase 11 — Alerting ✓
- [x] Prometheus alerting rules: NodeDown (critical), HighCPU/Memory/Disk/Temperature (warning)
- [x] AlertManager service (Docker Compose, port 9093) with grouping and repeat intervals
- [x] Backend `/api/v1/alerts` endpoint proxies Prometheus alert state, sorted by severity
- [x] AlertsPanel on dashboard: all-clear state, firing/pending badges, severity color, duration
- [x] Panel border changes to amber/red when alerts are active

## Phase 10 — Node Exporter ✓
- [x] prometheus/node-exporter DaemonSet on all 4 K3s nodes via ArgoCD (k8s/apps/node-exporter.yaml)
- [x] Prometheus scrape job for node-exporter with per-node node_name labels
- [x] Grafana dashboard rewritten with node_exporter metrics (CPU %, memory %, disk %, temp, network)
- [x] Two new panels: Network Receive and Network Transmit per node
- [x] SSH metric collection retained for health card status; Grafana uses native Prometheus data

## Phase 9 — Audit Logging ✓
- [x] `audit_logs` table: action, resource_type, resource_name, actor, status, detail, timestamp
- [x] AuditService wraps all writes with best-effort semantics (never breaks the operation)
- [x] Audit events captured for: workload create/delete, node cordon/uncordon (success + failure)
- [x] Actor resolved from JWT-authenticated user on every mutation
- [x] GET /api/v1/audit with limit/offset pagination
- [x] Audit Log page in frontend: event table, action/status badges, filter by type, load more

## Phase 13 — Pod Log Viewer ✓
- [x] `GET /workloads/{name}/logs?tail=N` — reads last N lines from a running pod via K8s API
- [x] Selects a Running pod first, falls back to first available pod
- [x] Auth-protected (any authenticated user); returns workload name, pod name, log text
- [x] LogsModal component: dark terminal viewport, auto-scrolls to bottom, Refresh button, Esc/overlay-click to close
- [x] "Logs" button per row in workloads table; opens modal without leaving the page

## Phase 12 — Workload Scaling ✓
- [x] `PATCH /workloads/{name}/scale` endpoint with replica range validation (1–10)
- [x] K8s `patch_namespaced_deployment` applies replica count immediately
- [x] DB `update_replicas` keeps workload record in sync
- [x] Audit logged on every scale operation (success + failure)
- [x] Inline − / count / + controls in workloads table; disabled at bounds or while scaling

## Phase 8 — Load Balancing ✓
- [x] Traefik DaemonSet deployed on K3s (HostPort 80/443, IngressClass traefik)
- [x] Workload API creates K8s Service + Ingress on container_port
- [x] TLS termination via Traefik built-in self-signed cert
- [x] Ingress host auto-assigned as `<name>.pi-cluster.local`
- [x] Frontend shows ingress URL as clickable link in workloads table
