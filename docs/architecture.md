# Pi-Cluster Architecture

## 1. Overview

Pi-Cluster is a self-hosted DevOps control platform for monitoring, deploying, and managing containerised workloads on a Raspberry Pi cluster.

The architecture separates:

- Web UI
- REST API
- Business logic
- Persistent data
- Cache and distributed coordination
- Metrics collection and visualisation
- Alerting
- CI/CD delivery
- Kubernetes orchestration
- GitOps manifest management
- Container image registry
- Log aggregation
- Backup & disaster recovery

---

## 2. Physical Infrastructure

### Network

```
Subnet:  10.100.102.0/24
Router:  10.100.102.1
Switch:  10.100.102.200
```

### Nodes

| Node     | IP             | Role                       |
|----------|----------------|----------------------------|
| pi-node1 | 10.100.102.10  | Control plane + platform   |
| pi-node2 | 10.100.102.16  | K3s worker                 |
| pi-node3 | 10.100.102.17  | K3s worker                 |
| pi-node4 | 10.100.102.12  | K3s worker                 |

**pi-node1** hosts the entire platform stack via Docker Compose. It also runs the K3s control plane (API server, scheduler, controller-manager, etcd).

**pi-node2/3/4** run only the K3s agent. They receive and execute workloads scheduled by the K3s control plane.

All SSH access to pi-node1 uses key-based authentication (`alex@10.100.102.10`). Password authentication is disabled. Application code lives at `/opt/pi-cluster`.

---

## 3. High-Level Component Map

```
  Developer laptop
        │  git push
        ▼
  GitHub (master branch)
        │
   ┌────┴─────────────────────┐
   │                          │
   │ Jenkins SCM poll (2 min) │ ArgoCD poll (~3 min)
   ▼                          ▼
  Jenkins (Docker, :8080)   ArgoCD (K3s, :30443)
   │                          │
   │ rsync → docker compose   │ kubectl apply k8s/apps/
   ▼                          ▼
  pi-node1 Docker Compose   K3s cluster (all 4 nodes)
```

These are two independent delivery pipelines. Jenkins owns the Docker Compose stack (backend, DB, monitoring). ArgoCD owns K8s manifests in `k8s/apps/` (node-exporter DaemonSet, Traefik DaemonSet).

---

## 4. Frontend

**Technology:** React + TypeScript + Vite, served via Nginx at `:80`.

The frontend communicates exclusively with the FastAPI backend. It never:
- holds SSH credentials
- communicates directly with Raspberry Pi nodes
- queries Prometheus, Grafana, or K8s directly
- contains infrastructure secrets

Pages: Dashboard, Workloads, Audit Log.

---

## 5. Backend

**Technology:** Python + FastAPI + Pydantic + SQLAlchemy (async) + Alembic.

Layered architecture — business logic and data access are strictly separated:

```
  API Route   ← HTTP, auth dependency, schema validation
      ↓
  Service     ← business logic, K8s operations, SSH calls, audit logging
      ↓
  Repository  ← SQLAlchemy async queries only, no business logic
      ↓
  PostgreSQL
```

The backend also integrates with:
- **Kubernetes Python client** — all K8s control operations (deploy, scale, update, evict, cordon/drain)
- **Paramiko** — SSH to Pi nodes for health metrics
- **Redis** — caching health results (90s TTL), distributed locks
- **Prometheus HTTP API** — proxying active alert state to the frontend

---

## 6. PostgreSQL

PostgreSQL is the persistent source of truth for:

- Users and roles
- Cluster node inventory
- Workload records (desired state: image, replicas, resource limits, probe paths, env vars)
- Audit log

**Not stored in PostgreSQL:** live metrics (those belong in Prometheus), Kubernetes live state (queried directly from K8s).

---

## 7. Redis

Redis provides fast ephemeral storage and coordination:

- Node health cache — 90s TTL per node, prevents SSH spam on every dashboard load
- Distributed locks — prevent concurrent conflicting operations on the same node

Redis is not the persistent source of truth and cannot replace PostgreSQL.

---

## 8. Metrics — Prometheus + node-exporter

node-exporter runs as a DaemonSet on all four K3s nodes (managed by ArgoCD). It exposes hardware metrics on port 9100.

Prometheus (Docker Compose, `:9090`) scrapes node-exporter on all four nodes every 15 seconds with a `node_name` label per node.

The backend also exposes a `/metrics` endpoint (prometheus-fastapi-instrumentator) for API-level metrics.

```
  node-exporter (:9100) on each node
        │  scrape every 15s
        ▼
  Prometheus (:9090)
        │
        ├── evaluate alert rules → AlertManager (:9093)
        │                                │
        │                                └── /api/v1/alerts → dashboard
        │
        └── query API → Grafana (:3000)
```

**Custom Prometheus Gauges** (from SSH, for per-node health cards):
`node_cpu_percent`, `node_ram_percent`, `node_disk_percent`, `node_temp_celsius`, `node_uptime_seconds`.

**Grafana** is auto-provisioned (datasource + dashboard) and shows 10 panels: CPU, RAM, Disk, Temperature, Network Rx/Tx — all per node, all from node-exporter metrics.

---

## 9. Alerting — Prometheus Rules + AlertManager

Alerting rules are defined in `prometheus/alerts.yml` and evaluated by Prometheus.

| Rule | Severity | Condition |
|---|---|---|
| NodeDown | critical | node-exporter unreachable > 2 min |
| HighCPU | warning | CPU% > 85% sustained 5 min |
| HighMemory | warning | RAM% > 80% sustained 5 min |
| HighDisk | warning | Disk% > 85% sustained 5 min |
| HighTemperature | warning | Temp > 70°C sustained 5 min |

AlertManager (`:9093`) handles grouping and repeat intervals. The backend proxies the Prometheus alert state to the frontend via `GET /api/v1/alerts` — the frontend never queries Prometheus directly.

---

## 10. SSH

SSH (via Paramiko) is used for node health checks only:

- CPU usage percent
- Memory usage percent
- Disk usage percent
- CPU temperature
- Uptime seconds

SSH credentials are held exclusively in backend environment variables. The frontend never sees them. Arbitrary shell execution is not exposed through the API — all SSH commands are explicitly defined in `SSHService`.

The primary SSH target for platform operations is `alex@10.100.102.10` using key-based auth.

---

## 11. CI/CD — Jenkins

Jenkins runs as a Docker container on pi-node1 (`:8080`). It polls GitHub every 2 minutes and triggers the pipeline on any push to `master`.

Pipeline stages:

1. **Checkout** — clone `master` from GitHub
2. **Sync** — rsync workspace to `/opt/pi-cluster` on pi-node1
3. **Deploy** — `docker compose up -d --build backend frontend`
4. **Migrate** — `alembic upgrade head` inside the backend container
5. **Health Check** — `curl -sf http://10.100.102.10:8000/health`

Jenkins has direct LAN access to all nodes and is not exposed to the internet.

---

## 12. Kubernetes — K3s

K3s runs the container orchestration layer:

- **Control plane** on pi-node1 (API server, scheduler, controller-manager, etcd)
- **Agents** on pi-node2/3/4

The FastAPI backend communicates with K3s via the Kubernetes Python client using a kubeconfig file stored on pi-node1.

Workload operations performed through the backend:
- Create/delete Deployment, Service, Ingress
- Patch Deployment (scale, image, env, resources, probes, restartedAt annotation)
- List pods, read logs, list events
- Cordon/uncordon nodes, drain nodes (eviction API)
- Read node capacity (allocatable vs requested)

---

## 13. GitOps — ArgoCD

ArgoCD (K3s, NodePort `:30443`) watches the `k8s/apps/` directory in the GitHub repository and automatically applies changes to the K3s cluster.

```
k8s/
└── apps/
    ├── node-exporter.yaml    ← prometheus/node-exporter DaemonSet on all 4 nodes
    └── traefik.yaml          ← Traefik DaemonSet + RBAC
```

ArgoCD does **not** manage the Docker Compose stack — that is Jenkins's responsibility.

**Sync policy:** automated with `prune: true` and `selfHeal: true`. Any change to `k8s/apps/` in Git is applied within ~3 minutes. Manual `kubectl apply` is not needed for resources in this directory.

---

## 14. Ingress — Traefik

Traefik runs as a DaemonSet on all K3s nodes (managed by ArgoCD), binding ports 80 and 443 via HostPort.

When a workload is deployed with a `container_port`, the backend creates:
1. A K8s `Service` targeting `container_port`
2. A Traefik `Ingress` with host `<name>.pi-cluster.local`
3. TLS termination via Traefik's built-in self-signed certificate

The frontend shows the ingress URL as a clickable link in the workloads table.

---

## 15. Audit Logging

Every mutating operation is recorded in the `audit_logs` table:

| Field | Description |
|---|---|
| action | e.g. `workload.create`, `node.drain`, `workload.scale` |
| resource_type | `workload` or `node` |
| resource_name | name of the affected resource |
| actor | username from the authenticated JWT |
| status | `success` or `failure` |
| detail | human-readable outcome or error message |
| created_at | UTC timestamp |

Audit writes use best-effort semantics — a failed audit write never breaks the underlying operation.

The `GET /api/v1/audit` endpoint supports server-side filtering by `status` and `resource_type`, plus `limit`/`offset` pagination.

---

## 16. Node State Model

Nodes report one of four health states, derived from SSH metric collection:

```
ONLINE    ← all metrics collected successfully
DEGRADED  ← metrics collected but values indicate a problem
OFFLINE   ← SSH connection failed or timed out
UNKNOWN   ← not yet polled
```

Health polling runs as a background asyncio task every 30 seconds. A single node being OFFLINE or DEGRADED does not affect the dashboard or API for other nodes.

---

## 17. Security

- JWT tokens for all authenticated endpoints; admin role required for all mutating operations
- SSH credentials in backend `.env` only — never logged, never sent to the frontend
- No arbitrary shell execution through the API — all SSH commands are explicit and predefined
- Secrets in `.env`, excluded from Git via `.gitignore`
- SSH key auth required for pi-node1; password auth disabled
- Audit log provides a non-repudiation trail for every cluster operation

---

## 18. Design Principles

- Separation of concerns: API routes own HTTP; services own logic; repositories own data access
- Dependency injection: services and repositories are injected, not instantiated in routes
- Typed APIs: Pydantic for Python, strict TypeScript for the frontend
- Incremental development: one phase at a time, no premature abstraction
- Testability: services are independently testable without HTTP or DB dependencies
- Node failure isolation: one node being unreachable never breaks the dashboard for others

## 19. Backups & Disaster Recovery

`ansible/roles/backup` schedules a nightly (02:30) cron job on pi-node1 that backs up:

- **Postgres** — `pg_dump` of the `pi_cluster` database via `docker exec pi-cluster-postgres-1`, gzipped
- **K3s datastore** — a SQLite online backup of `/var/lib/rancher/k3s/server/db/state.db`, plus a tarball of `/etc/rancher/k3s` and the server TLS directory. pi-node1 runs single-server K3s with the embedded SQLite/kine datastore, not etcd — see `docs/decisions.md`.

Both are shipped via `rsync` over a dedicated SSH key (`/home/alex/.ssh/id_backup`) to **pi-node4** (10.100.102.12), the intentional off-node target. Local copies on pi-node1 are trimmed to the last 3; remote copies on pi-node4 to the last 14.

**Not part of the GitOps/Jenkins auto-deploy path** — apply with:

```
cd ansible && ansible-playbook -i inventory/hosts.ini playbooks/backup.yml
```

Safe to re-run (key generation, `authorized_keys`, and cron are all idempotent).

### Restore

1. **Postgres**: `gunzip -c postgres.sql.gz | docker exec -i pi-cluster-postgres-1 psql -U pi_cluster pi_cluster`
2. **K3s datastore**: stop k3s (`systemctl stop k3s`), replace `/var/lib/rancher/k3s/server/db/state.db` with the backed-up copy, restore `/etc/rancher/k3s` and the server TLS directory from `k3s-certs.tar.gz`, restart k3s.

This runbook has not yet been exercised end-to-end against pi-node1 — treat step 2 as a starting point, not a verified procedure, until it's been tested once.

## 20. Container Registry

`registry:2` runs as a Docker Compose service on pi-node1 (`:5000`, `registry-data` volume). Jenkins tags the platform's own `backend`/`frontend` images with the short git SHA and `latest` and pushes both after a successful health check (`Jenkinsfile`'s `Push to Registry` stage) — this gives the platform's own image history a rollback trail independent of `docker compose build`'s local cache. No authentication is configured (see `docs/decisions.md`); it is not exposed beyond the LAN.

## 21. Log Aggregation

Loki (`loki` Compose service, `:3100`, filesystem storage) and Promtail (K3s DaemonSet, `k8s/apps/promtail.yaml`, ArgoCD-applied) give the platform a single place to search logs instead of switching between the in-app pod log viewer, `docker compose logs`, and SSH.

Promtail runs on all 4 nodes and scrapes two sources: K3s pod logs (`/var/log/pods`, all nodes) and Docker Compose container logs (`/var/lib/docker/containers`, pi-node1 only — empty elsewhere). Both push to `http://10.100.102.10:3100/loki/api/v1/push`. Grafana has a Loki datasource provisioned alongside the existing Prometheus one, so logs and metrics live in the same dashboard tool.

Loki's own log retention (`loki/loki-config.yml`, `retention_period: 30d`) is independent of the backend's `LOG_RETENTION_DAYS` — see §22 and `docs/decisions.md`.

## 22. Log & Audit Retention

The backend runs a daily background job (`poll_retention_forever`, alongside the health and alert pollers in `main.py`'s lifespan) that deletes `audit_logs` rows and **resolved** `alert_history` rows older than `LOG_RETENTION_DAYS` (`.env`, default 90). Active/unresolved alerts are never deleted regardless of age.

This is scoped strictly to those two Postgres tables. It does not touch Loki's or Prometheus's storage (§21) — each service that persists its own data is expected to manage its own retention rather than being swept by this job.
