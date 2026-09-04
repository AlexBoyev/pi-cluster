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

**pi-node1** hosts the entire platform stack via Docker Compose. It also runs the K3s control plane (API server, scheduler, controller-manager, and the embedded SQLite/kine datastore — this is single-server K3s, not etcd; see `docs/decisions.md`).

**pi-node2/3/4** run only the K3s agent. They receive and execute workloads scheduled by the K3s control plane.

SSH access to pi-node1 is as `admin@10.100.102.10`. Both key-based (interactive/operator sessions) and password-based auth are enabled — the backend's own health-check SSH client (`SSHService`) authenticates with a password (`SSH_PASSWORD` in `.env`), so password auth is not disabled. Application code lives at `/home/admin/pi-cluster` (the path Jenkins actually deploys to — see `docs/decisions.md` for why this differs from Ansible's `platform_dir`). A separate `alex` identity exists for Ansible-managed automation only (`ansible_user: alex` in `ansible/group_vars/all.yml`) — not the identity used for day-to-day operator SSH.

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

The primary SSH target for platform operations is `admin@10.100.102.10` (key-based for operator sessions; password-based for the backend's own health-check client — see §2).

---

## 11. CI/CD — Jenkins

Jenkins runs as a Docker container on pi-node1 (`:8080`). It polls GitHub every 2 minutes and triggers the pipeline on any push to `master`.

Pipeline stages:

1. **Checkout** — clone `master` from GitHub
2. **Sync** — rsync workspace to `/home/admin/pi-cluster` on pi-node1
3. **Deploy** — `docker compose up -d --build backend frontend`
4. **Migrate** — `alembic upgrade head` inside the backend container
5. **Health Check** — `curl -sf http://10.100.102.10:8000/health`

Jenkins has direct LAN access to all nodes and is not exposed to the internet.

---

## 12. Kubernetes — K3s

K3s runs the container orchestration layer:

- **Control plane** on pi-node1 (API server, scheduler, controller-manager, embedded SQLite/kine datastore — not etcd)
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

ArgoCD (K3s, NodePort `:30443`) watches **only** the `k8s/apps/` directory (`spec.source.path` on the `pi-cluster` Application — verify with `kubectl get application pi-cluster -n argocd -o jsonpath='{.spec.source.path}'` if this ever needs re-confirming) and automatically applies changes to the K3s cluster.

```
k8s/
├── apps/
│   ├── namespace.yaml              ← pi-apps namespace
│   ├── node-exporter.yaml          ← node-exporter DaemonSet, all 4 nodes
│   ├── promtail.yaml                ← Promtail DaemonSet, all 4 nodes
│   ├── kube-state-metrics.yaml     ← kube-state-metrics Deployment + NodePort
│   └── sample-nginx.yaml           ← example workload
└── traefik/
    └── traefik.yaml                 ← Traefik DaemonSet + RBAC — NOT under k8s/apps/, NOT GitOps-managed
```

**`k8s/traefik/traefik.yaml` is a documentation trap** — it looks like it belongs with the other K8s manifests, but ArgoCD never watches it. It was applied once by hand (Phase 8) and any change to it since requires a manual `kubectl apply -f k8s/traefik/traefik.yaml` — pushing to git alone does nothing. Discovered the hard way while deploying the pi-node1 exclusion fix (see `docs/decisions.md`). Worth moving into `k8s/apps/` at some point so it stops being a special case; not done as of this writing.

ArgoCD does **not** manage the Docker Compose stack — that is Jenkins's responsibility.

**Sync policy:** automated with `prune: true` and `selfHeal: true`. Any change to `k8s/apps/` in Git is applied within ~3 minutes. Manual `kubectl apply` is not needed for resources in that directory — but is needed for `k8s/traefik/`, per above.

---

## 14. Ingress — Traefik

Traefik runs as a DaemonSet on pi-node2/3/4 (managed by ArgoCD), binding ports 80 and 443 via HostPort. Excluded from pi-node1 via node affinity — Docker Compose's `nginx` already binds those host ports there, and Traefik crash-loops if scheduled alongside it. See `docs/decisions.md`.

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
- SSH to pi-node1 as `admin@10.100.102.10`: key-based for operators, password-based for the backend's own `SSHService` health checks (`SSH_PASSWORD` in `.env`, never sent to the frontend)
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

Both are shipped via `rsync` over a dedicated SSH key (`/home/admin/.ssh/id_backup`) to **pi-node4** (10.100.102.12), the intentional off-node target. Local copies on pi-node1 are trimmed to the last 3; remote copies on pi-node4 to the last 14.

**Not part of the GitOps/Jenkins auto-deploy path** — apply with:

```
cd ansible && ansible-playbook -i inventory/hosts.ini playbooks/backup.yml
```

Safe to re-run (key generation, `authorized_keys`, and cron are all idempotent).

### Restore

1. **Postgres**: `gunzip -c postgres.sql.gz | docker exec -i pi-cluster-postgres-1 psql -U pi_cluster pi_cluster`
2. **K3s datastore**: stop k3s (`systemctl stop k3s`), replace `/var/lib/rancher/k3s/server/db/state.db` with the backed-up copy, restore `/etc/rancher/k3s` and the server TLS directory from `k3s-certs.tar.gz`, restart k3s.

Step 1 (Postgres) has been exercised for real: restored into a scratch database and row counts (`users`, `workloads`, `audit_logs`, `nodes`) matched production exactly. Step 2 (K3s datastore) has not — treat it as a starting point, not a verified procedure, until it's been tested once (lower urgency, higher blast radius to rehearse than the Postgres path — stopping k3s on the live control plane to test a restore is a bigger ask than a scratch-database drill).

## 20. Container Registry

`registry:2` runs as a Docker Compose service on pi-node1 (`:5000`, `registry-data` volume). Jenkins tags the platform's own `backend`/`frontend` images with the short git SHA and `latest` and pushes both after a successful health check (`Jenkinsfile`'s `Push to Registry` stage) — this gives the platform's own image history a rollback trail independent of `docker compose build`'s local cache. No authentication is configured (see `docs/decisions.md`); it is not exposed beyond the LAN.

## 21. Log Aggregation

Loki (`loki` Compose service, `:3100`, filesystem storage) and Promtail (K3s DaemonSet, `k8s/apps/promtail.yaml`, ArgoCD-applied) give the platform a single place to search logs instead of switching between the in-app pod log viewer, `docker compose logs`, and SSH.

Promtail runs on all 4 nodes and scrapes two sources: K3s pod logs (`/var/log/pods`, all nodes) and Docker Compose container logs (`/var/lib/docker/containers`, pi-node1 only — empty elsewhere). Both push to `http://10.100.102.10:3100/loki/api/v1/push`. Grafana has a Loki datasource provisioned alongside the existing Prometheus one, so logs and metrics live in the same dashboard tool.

Loki's own log retention (`loki/loki-config.yml`, `retention_period: 30d`) is independent of the backend's `LOG_RETENTION_DAYS` — see §22 and `docs/decisions.md`.

## 22. Log & Audit Retention

The backend runs a daily background job (`poll_retention_forever`, alongside the health and alert pollers in `main.py`'s lifespan) that deletes `audit_logs` rows and **resolved** `alert_history` rows older than `LOG_RETENTION_DAYS` (`.env`, default 90). Active/unresolved alerts are never deleted regardless of age.

This is scoped strictly to those two Postgres tables. It does not touch Loki's or Prometheus's storage (§21) — each service that persists its own data is expected to manage its own retention rather than being swept by this job.

## 23. Household Services

A separate category from everything above: self-hosted apps for household use (2 users) that happen to run on this cluster, not part of the platform itself — they don't manage nodes, workloads, or each other. Wallabag (read-later) is the first; Vikunja, Paperless-ngx, and Firefly III are planned to follow the same pattern. Full reasoning in `docs/decisions.md`'s Wallabag ADR — this section is the pattern summary, kept current as more services land.

**The pattern, established once and reused:**

- **One namespace per service** (`wallabag`, eventually `vikunja`, `paperless`, `firefly`) — own `ResourceQuota`, clean uninstall, no cross-service Service-name collisions.
- **Storage**: `local-path` StorageClass + `nodeSelector` pinning the Deployment to a specific worker — not NFS (no NFS infrastructure exists on this cluster; see the ADR for why that's a deliberate choice, not a gap). Each service's data is physically tied to one node. Consequence: draining that node makes the service `Pending`, not rescheduled — see `docs/operations.md` for the drain-impact table and manual node-migration procedure.
- **Database**: a dedicated Postgres role + database inside the existing platform Postgres (`10.100.102.10:5432`, reached over the LAN from K8s pods, since Postgres runs in Docker Compose, not K8s) — not a new Postgres pod per service, not SQLite. Each new database must be added to `ansible/roles/backup`'s `backup_postgres_databases` list, or it silently isn't backed up.
- **Secrets**: created manually with `kubectl create secret`, documented per-service in that service's `k8s/apps/<name>/README.md`. Never committed — a Secret manifest in git under `k8s/apps/` would be continuously overwritten by ArgoCD's `selfHeal`, clobbering whatever real value was set manually.
- **Ingress**: a K8s `Ingress` resource with `ingressClassName: traefik` and a `<name>.pi-cluster.lan` host — nothing else required. nginx's wildcard fallback (§ below) and Traefik's DaemonSet on pi-node2/3/4 already handle routing for any hostname on that pattern; no nginx edit, no Jenkins deploy, no platform change per new service.
- **Node placement**: pi-node1 takes no household-service workloads (control plane + Docker Compose stack only). Each service is pinned to a specific worker by convention, not left to the scheduler — pi-node3 for Wallabag, pi-node2 reserved for Paperless, pi-node4 doubles as the backup target.
- **Monitoring**: relies on existing cluster-level tooling — `kube-state-metrics` + the `PodCrashLooping`/`PodNotReady` alert rules (§ Pod-Level Alerting, `prometheus/alerts.yml`) already cover any namespace, and Promtail already scrapes pod logs cluster-wide into Loki. A new household service does not need its own alert rule or logging setup by default; add one only if it needs alerting beyond "is the pod up."

**Ingress routing path**: `*.pi-cluster.lan`/`*.cluster.download` (dnsmasq wildcard) → nginx on pi-node1 → wildcard fallback `server` block (any hostname not matching a specific platform block) → `upstream` of all three workers with passive health checks → Traefik (whichever worker answers) → K8s `Ingress` → Service → pod. See `nginx/nginx.conf` and the ADR for why this replaced an earlier per-hostname-block idea.
