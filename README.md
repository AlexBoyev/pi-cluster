# Pi-Cluster

A self-hosted DevOps platform for a 4-node Raspberry Pi cluster. Provides a React dashboard for deploying, monitoring, and managing containerised workloads on Kubernetes, with a full CI/CD pipeline, GitOps delivery, Prometheus metrics, audit logging, SSH terminal, and live log streaming — all running on the cluster itself.

Alongside the platform, the cluster also hosts a small set of household services (Wallabag, Vikunja) behind a single-sign-on gate and per-service auto-login bridge, and a security-alert notification path (new-login-IP detection, severity-filtered email/webhook channels via a Brevo SMTP relay) — see [Household Services & SSO](#household-services--sso) and [Security](#security) below.

---

## Access

| Location | URL |
|---|---|
| Home WiFi | `http://pi-cluster.lan` |
| Public (anywhere) | `http://pi.cluster.download` |
| Direct IP | `http://10.100.102.10` |

DNS is handled by a dnsmasq container on pi-node1. On home WiFi, `*.pi-cluster.lan` and `*.cluster.download` resolve directly to `10.100.102.10` (split-horizon). Public access is via Cloudflare Tunnel — no port forwarding required.

---

## Cluster nodes

| Node     | IP             | Role                  |
|----------|----------------|-----------------------|
| pi-node1 | 10.100.102.10  | Control plane + host  |
| pi-node2 | 10.100.102.16  | K3s worker            |
| pi-node3 | 10.100.102.17  | K3s worker            |
| pi-node4 | 10.100.102.12  | K3s worker            |

- Subnet `10.100.102.0/24`, router `10.100.102.1`, switch `10.100.102.200`
- **pi-node1** runs the full platform stack via Docker Compose (backend, PostgreSQL, Redis, Prometheus, Grafana, AlertManager, Jenkins)
- **pi-node2/3/4** run K3s agent and receive scheduled workloads via the Kubernetes control plane on pi-node1

---

## High-level architecture

```
  Developer laptop
        │
        │  git push
        ▼
  ┌─────────────┐
  │   GitHub    │
  └──────┬──────┘
         │
    ┌────┴──────────────────────┐
    │                           │
    │ SCM poll (2 min)          │ independent poll (~3 min)
    ▼                           ▼
  ┌─────────────┐         ┌─────────────┐
  │   Jenkins   │         │   ArgoCD    │
  │  (Docker)   │         │   (K3s)     │
  │  :8080      │         │  :30443     │
  └──────┬──────┘         └──────┬──────┘
         │                       │
         │ rsync + docker build  │ apply k8s/apps/**
         ▼                       ▼
  ┌─────────────────────────────────────────────────┐
  │                   pi-node1                      │
  │                                                 │
  │  ┌────────────┐  ┌──────────┐  ┌────────────┐  │
  │  │  FastAPI   │  │  Nginx   │  │  Jenkins   │  │
  │  │  Backend   │  │ (static) │  │            │  │
  │  │  :8000     │  │  :80     │  │  :8080     │  │
  │  └─────┬──────┘  └──────────┘  └────────────┘  │
  │        │                                        │
  │  ┌─────┴──────┐  ┌──────────┐  ┌────────────┐  │
  │  │ PostgreSQL │  │  Redis   │  │ Prometheus │  │
  │  │  :5432     │  │  :6379   │  │  :9090     │  │
  │  └────────────┘  └──────────┘  └─────┬──────┘  │
  │                                       │         │
  │  ┌────────────┐  ┌──────────────┐     │         │
  │  │  Grafana   │◄─┤AlertManager  │◄────┘         │
  │  │  :3000     │  │  :9093       │               │
  │  └────────────┘  └──────────────┘               │
  └─────────────────────────────────────────────────┘
         │
         │  K3s API + kubectl
         ▼
  ┌──────────────────────────────────────────┐
  │              K3s Cluster                 │
  │                                          │
  │  ┌──────────┐  ┌──────────────────────┐  │
  │  │  ArgoCD  │  │ node-exporter        │  │
  │  │          │  │ DaemonSet (:9100)    │  │
  │  └──────────┘  └──────────────────────┘  │
  │                                          │
  │  ┌──────────┐  ┌──────────────────────┐  │
  │  │ Traefik  │  │  User workloads      │  │
  │  │ Ingress  │  │  (Deployments)       │  │
  │  │ :80/:443 │  │  *.pi-cluster.lan  │  │
  │  └──────────┘  └──────────────────────┘  │
  │                                          │
  │  pi-node1 ─ pi-node2 ─ pi-node3 ─ pi-node4
  └──────────────────────────────────────────┘
```

---

## Stack

| Layer        | Technology                        | Purpose                                      |
|--------------|-----------------------------------|----------------------------------------------|
| Frontend     | React + TypeScript + Vite         | Dashboard UI                                 |
| Backend      | Python + FastAPI + SQLAlchemy     | REST API, business logic, K8s control        |
| Database     | PostgreSQL                        | Persistent state (nodes, workloads, audit)   |
| Cache        | Redis                             | Health cache (90s TTL), distributed locks    |
| Metrics      | Prometheus + node-exporter        | Time-series metrics scraped from all nodes   |
| Dashboards   | Grafana                           | Metric visualisation, 10 panels              |
| Alerting     | Prometheus rules + AlertManager   | NodeDown/HighCPU/RAM/Disk/Temp rules         |
| CI           | Jenkins (2 pipelines)             | Pre-merge gate + post-merge deploy           |
| Orchestration| K3s (Kubernetes)                  | Container scheduling across 4 nodes          |
| GitOps       | ArgoCD                            | Declarative K8s manifest delivery            |
| Ingress      | Traefik DaemonSet                 | HTTP/S routing + TLS for workloads           |
| Reverse proxy| nginx                             | Single entry point on pi-node1: platform hostnames, household-services SSO gate, LAN restrictions |
| DNS          | dnsmasq                           | LAN wildcard DNS + split-horizon for public domain |
| Tunnel       | Cloudflare Tunnel (cloudflared)   | Public access without port forwarding        |
| Log aggregation | Loki + Promtail                | Centralised logs from K3s pods + Compose containers |
| Household services | Wallabag, Vikunja            | Self-hosted apps for household use, gated by SSO — see below |
| Mailer       | Brevo SMTP relay                  | Vikunja reminders + security-alert email notifications |
| Config Mgmt  | Ansible                           | Node bootstrap, K3s install, platform deploy |
| K8s Packaging| Helm                              | Platform chart (backend, frontend, DB, Redis)|
| IaC          | Terraform (K8s + Helm providers)  | Namespaces, RBAC, ArgoCD Application         |

---

## Backend API layers

```
  HTTP Request
       │
  ┌────▼────────┐
  │  API Route  │  ← FastAPI router, auth dependency, schema validation
  └────┬────────┘
       │
  ┌────▼────────┐
  │   Service   │  ← Business logic, K8s operations, audit logging
  └────┬────────┘
       │
  ┌────▼────────┐
  │ Repository  │  ← SQLAlchemy async queries, no business logic
  └────┬────────┘
       │
  ┌────▼────────┐
  │ PostgreSQL  │
  └─────────────┘
```

Business logic and database queries are never in API routes. K8s operations always go through `K8sService`, never directly from routes.

---

## CI/CD — Jenkins

Jenkins is the **continuous delivery engine**. Two pipelines are configured:

### Jenkinsfile — post-merge deploy (master)

Every push to `master` is detected via SCM polling (every 2 minutes) and runs the full pipeline:

```
  ┌───────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐   ┌──────────────┐
  │ Checkout  │──▶│   Sync   │──▶│  Build   │──▶│  Test    │──▶│ Deploy  │──▶│   Migrate    │──▶ Health Check
  └───────────┘   └──────────┘   └──────────┘   └──────────┘   └─────────┘   └──────────────┘
  Clone repo      rsync to        docker build    pytest          compose up    alembic           curl /health
  from GitHub     pi-node1        backend image   (310 tests)     --build       upgrade head
```

| Stage | What it does |
|---|---|
| **Checkout** | Clones `master` from GitHub into the Jenkins workspace |
| **Sync** | `rsync` copies the workspace to `/home/admin/pi-cluster` on pi-node1 |
| **Build** | `docker compose build backend` — builds the backend image |
| **Test** | `pytest` against all 310 tests using an in-process SQLite DB |
| **Deploy** | `docker compose up -d --build backend frontend` — restarts containers |
| **Migrate** | Waits 5 s, then runs `alembic upgrade head` inside the backend container |
| **Health Check** | Waits 10 s, then `curl -sf http://10.100.102.10:8000/health` |

### Jenkinsfile.test — pre-merge gate (all branches)

Polls all branches every 3 minutes. Runs Checkout → Sync → Build → Test without deploying. Reports "safe to merge" or "do NOT merge" in the build result. Use this to catch failures before merging feature branches.

---

## GitOps — ArgoCD

ArgoCD watches `k8s/apps/` in this repository and applies changes to K3s automatically. It does not manage the Docker Compose stack — that is Jenkins's job.

### Scope

```
k8s/
└── apps/
    ├── node-exporter.yaml    ← prometheus/node-exporter DaemonSet (all 4 nodes)
    └── traefik.yaml          ← Traefik DaemonSet + RBAC (HostPort 80/443)
```

### Reading the ArgoCD UI

- **SYNC STATUS: Synced** → cluster matches what is in `k8s/apps/` at HEAD.
- **Last Sync commit** shows the last commit that changed a file inside `k8s/apps/`. If recent commits only changed `backend/` or `frontend/`, ArgoCD has nothing new to apply — "Synced to HEAD" is correct and expected.

---

## Household Services & SSO

A separate category from the platform itself: self-hosted apps for household use (2 users) that happen to run on this cluster — they don't manage nodes, workloads, or each other, and keep their own independent user systems. Full reasoning and every decision behind this pattern lives in `docs/decisions.md`'s ADRs and `docs/architecture.md` §23-25; this is the summary.

**Services today**: [Wallabag](https://wallabag.org) (read-later article archive, one shared account) and [Vikunja](https://vikunja.io) (shared task/project management, two real distinct accounts, CalDAV sync). Paperless-ngx and Firefly III are planned to follow the same pattern.

**The pattern**: one dedicated K8s namespace per service, `local-path` storage pinned to a specific worker node (not NFS — no NFS infrastructure exists on this cluster), a dedicated database + role inside the existing platform Postgres (not a new pod per service), an out-of-band `kubectl create secret` (never committed — ArgoCD's `selfHeal` would fight a Secret manifest in git), and a plain K8s `Ingress` with an `ingressClassName: traefik` and a `<name>.pi-cluster.lan` host — nginx's wildcard fallback and Traefik already handle routing for any hostname on that pattern, no nginx edit or platform deploy needed per new service.

**SSO gate**: you can't reach any household service at all without an active pi-cluster session. Logging into the platform sets a second cookie (`pi_sso`, `Domain=.pi-cluster.lan`, `HttpOnly`) alongside the SPA's normal JWT flow. nginx's wildcard `server` block runs `auth_request` against `GET /api/v1/auth/verify` on every request; no valid cookie redirects to the platform login instead of ever reaching Traefik. This gates *reachability* only — each service still has its own separate login once you're through.

**Auto-login bridge**: on top of the gate, a per-service bridge (`WallabagBridgeService`, `VikunjaBridgeService`) logs the current pi-cluster user into the target service server-side and hands off the resulting session via a two-hop redirect through the service's own origin, so the household-service dashboard tile can skip that service's login screen entirely. Wallabag has one shared account (the bridge always uses it); Vikunja has two real distinct accounts, so its bridge looks up the calling user's own Vikunja login from a small credential map (`VIKUNJA_BRIDGE_CREDENTIALS` in `.env`).

**CalDAV is exempt from the SSO gate**: Vikunja needs to work from phones on mobile data over CalDAV, and CalDAV clients (DAVx5, iOS) authenticate with plain HTTP Basic Auth — they cannot follow a redirect to an HTML login page. `/dav/*` is carved out of the gate entirely in `nginx/nginx.conf`, relying on Vikunja's own per-user CalDAV app-password instead (never the account password — also Vikunja's own mitigation for CalDAV's inherent Basic-Auth-can-bypass-2FA risk).

**Mail**: Vikunja's due-date reminders go through a Brevo SMTP relay (`BREVO_SMTP_*` in `.env`) — a free-tier relay, not a personal mailbox, chosen for machine-generated transactional mail. The same relay account also delivers security-alert email (see [Security](#security)) under a distinct `alerts@` sender address.

Manual per-service setup (Postgres role, Secret, first accounts, CalDAV client setup) is documented in each service's own `k8s/apps/<name>/README.md` and in `docs/operations.md` (deploy, upgrade, add-a-user, and troubleshooting runbooks).

---

## Node management

Each node card on the dashboard exposes:

- **SSH Terminal** — in-browser interactive shell into any cluster node via a WebSocket proxy (backend dials SSH with stored credentials, forwards I/O)
- **Details** — live Prometheus time-series charts for CPU, RAM, disk, and temperature (1h / 6h / 24h range)
- **Restart** / **Shutdown** — per-node reboot or poweroff via SSH

The dashboard header provides **Restart All** / **Shutdown All** cluster-wide controls, each guarded by a confirmation dialog.

---

## Workload lifecycle

```
  Deploy ──▶ Scale ──▶ Update image ──▶ Set env vars ──▶ Set resource limits ──▶ Delete
     │                                                                                │
     ├──▶ Configure health probes (liveness + readiness HTTP)                        │
     │                                                                                │
     ├──▶ Rolling restart (restartedAt annotation patch)                             │
     │                                                                                │
     ├──▶ Rollback (K8s revision history)                                            │
     │                                                                                │
     ├──▶ Horizontal Pod Autoscaler (min/max replicas, CPU target)                   │
     │                                                                                │
     ├──▶ Drain node (cordon + evict all pods)                                       │
     │                                                                                │
     ├──▶ View pods (phase, ready count, node, IP, age)                              │
     │                                                                                │
     ├──▶ Live log streaming per pod (WebSocket, last N lines + follow)              │
     │                                                                                │
     ├──▶ Pod exec terminal (in-browser shell into running container)                │
     │                                                                                │
     └──▶ View K8s events (Warning/Normal, age-sorted)
```

Every operation:
- Uses the Kubernetes Python client against the K3s API on pi-node1
- Updates the PostgreSQL workload record to keep the DB in sync
- Is audit-logged with actor, timestamp, result, and detail
- Triggers a K8s rolling restart where applicable (image, env, resources, probes)

The workloads table auto-refreshes every 15 seconds. Polling pauses while any modal is open. Columns are sortable. Workloads can be filtered by status or searched by name.

### Other K8s resources managed via the dashboard

| Resource | Operations |
|---|---|
| StatefulSets / DaemonSets | List, scale, delete |
| CronJobs | List, suspend/resume, trigger now |
| Batch Jobs | List, delete |
| ConfigMaps | List, create, edit (YAML), delete |
| Secrets | List, create, delete (values masked) |
| Services / Ingresses | List, delete |
| PersistentVolumeClaims | List, create, delete |
| HPA | List, create (CPU target), delete |
| RBAC | Explorer: Roles, ClusterRoles, Bindings |
| Namespaces | List, create, delete (protected namespaces blocked) |
| Alert Rules | List current Prometheus rules |
| Helm releases | List (via Helm API) |

### Ingress

When a workload is deployed with a `container_port`, the backend creates a K8s Service and Traefik Ingress. The ingress host is auto-assigned as `<name>.pi-cluster.local` with TLS termination via Traefik's built-in self-signed certificate.

---

## Monitoring stack

```
  pi-node1/2/3/4
       │
  node-exporter DaemonSet (:9100) — CPU, memory, disk, network, temperature
       │  scrape every 15s
       ▼
  Prometheus (:9090)
       │                       │
       │ evaluate alert rules   │ query
       ▼                       ▼
  AlertManager (:9093)     Grafana (:3000)
       │                       │
       ▼                       │  10 dashboard panels:
  /api/v1/alerts               │    CPU % per node
  (proxied to frontend)        │    RAM % per node
                               │    Disk % per node
                               │    Temperature per node
                               └──  Network Rx/Tx per node
```

SSH-based metric collection is retained for node health card status (ONLINE/OFFLINE/DEGRADED/UNKNOWN). Grafana and Prometheus use native node-exporter data.

A background poller (30s interval) syncs Prometheus firing alerts to the `alert_history` table — recording each firing episode and stamping `resolved_at` when the alert clears. The **Alert History** page provides a searchable, filterable timeline of all past alert firings with duration and resolution status.

**Alerting rules** (`prometheus/alerts.yml`):

| Rule | Severity | Threshold |
|---|---|---|
| NodeDown | critical | node unreachable > 2 min |
| HighCPU | warning | CPU% > 85% for 5 min |
| HighMemory | warning | RAM% > 80% for 5 min |
| HighDisk | warning | Disk% > 85% for 5 min |
| HighTemperature | warning | CPU temp > 70°C for 5 min |

---

## Database schema

```
  nodes              workloads               audit_logs
  ─────              ─────────               ──────────
  id                 id                      id
  hostname           name (unique)           action
  ip_address         namespace               resource_type
  status             image                   resource_name
  cpu_count          replicas                actor
  memory_mb          ready_replicas*         status
  last_seen          target_node             detail
                     container_port          created_at
  users              ingress_host           known_login_ips
  ─────              env_vars (JSON)        ───────────────
  id                 cpu_limit              id
  username           memory_limit           user_id (FK → users)
  hashed_password    liveness_path          ip_address
  role               readiness_path         first_seen
                     status                 last_seen
  notification_      created_at
  channels                                  alert_history
  ────────────       * live from K8s,       ─────────────
  id                   not stored           id
  name                                      alert_name
  channel_type                              severity
  (webhook/email)                           node_name
  url                                       instance
  email_address                             summary
  min_severity                              labels (JSON)
  enabled                                   fired_at
                                             resolved_at
```

Migrations: `alembic/versions/` — 0001 through 0013 (0012 adds `known_login_ips` and `notification_channels.channel_type`/`email_address`; 0013 adds `notification_channels.min_severity`).

---

## API reference

All routes are prefixed `/api/v1/`. Authentication is JWT Bearer token (`Authorization: Bearer <token>`).

### Workloads

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/workloads/` | user | List all non-deleted workloads |
| POST | `/workloads/` | admin | Deploy new workload to K3s |
| GET | `/workloads/capacity` | user | Node CPU/RAM allocatable vs requested |
| PATCH | `/workloads/{name}/scale` | admin | Set replica count (1–10) |
| PATCH | `/workloads/{name}/image` | admin | Rolling image update |
| PATCH | `/workloads/{name}/env` | admin | Replace env vars (rolling restart) |
| PATCH | `/workloads/{name}/resources` | admin | Set CPU/memory limits |
| PATCH | `/workloads/{name}/probes` | admin | Set liveness/readiness HTTP probe paths |
| POST | `/workloads/{name}/restart` | admin | Rolling restart (restartedAt annotation) |
| POST | `/workloads/{name}/rollback` | admin | Roll back to previous K8s revision |
| GET | `/workloads/{name}/pods` | user | List pods with phase, ready count, node, IP |
| GET | `/workloads/{name}/metrics` | user | Live CPU/memory usage from Prometheus |
| GET | `/workloads/{name}/logs` | user | Last N pod log lines |
| GET | `/workloads/{name}/events` | user | K8s events for workload and its pods |
| DELETE | `/workloads/{name}` | admin | Delete deployment, service, and ingress |
| POST | `/workloads/nodes/{name}/cordon` | admin | Mark node unschedulable |
| DELETE | `/workloads/nodes/{name}/cordon` | admin | Mark node schedulable |
| POST | `/workloads/nodes/{name}/drain` | admin | Cordon + evict all non-DaemonSet pods |

### Nodes

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/nodes/` | user | Cluster node inventory |
| GET | `/nodes/{id}` | user | Single node detail |
| POST | `/nodes/` | admin | Register node |
| POST | `/nodes/{id}/restart` | admin | SSH reboot of a node |
| POST | `/nodes/{id}/shutdown` | admin | SSH shutdown of a node |
| POST | `/nodes/all/restart` | admin | Reboot all nodes simultaneously |
| POST | `/nodes/all/shutdown` | admin | Shutdown all nodes simultaneously |
| GET | `/nodes/{id}/metrics/history` | user | Prometheus time-series: CPU/RAM/disk/temp (1h/6h/24h) |

### WebSocket endpoints

| Path | Description |
|---|---|
| `/ws/exec/{name}?namespace=&token=` | Interactive shell into first running pod of a workload |
| `/ws/logs/{name}?namespace=&pod=&container=&tail=&token=` | Live log stream for a pod |
| `/ws/ssh/{node_ip}?token=` | Interactive SSH session to a cluster node |

### Kubernetes resources

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/cluster/capacity` | user | Cluster-wide CPU/memory: allocatable, requested, used |
| GET | `/events/` | user | K8s events — params: `namespace`, `event_type`, `limit` |
| GET | `/namespaces/` | user | List all K8s namespaces |
| POST | `/namespaces/` | admin | Create namespace |
| DELETE | `/namespaces/{name}` | admin | Delete namespace |
| GET | `/pods/` | user | List pods across namespaces |
| GET | `/configmaps/` | user | List ConfigMaps |
| POST | `/configmaps/` | admin | Create ConfigMap |
| PATCH | `/configmaps/{name}` | admin | Update ConfigMap data |
| DELETE | `/configmaps/{name}` | admin | Delete ConfigMap |
| GET | `/secrets/` | user | List Secrets (values masked) |
| POST | `/secrets/` | admin | Create Secret |
| DELETE | `/secrets/{name}` | admin | Delete Secret |
| GET | `/services/` | user | List Services and Ingresses |
| DELETE | `/services/{name}` | admin | Delete Service |
| GET | `/storage/` | user | List PVCs |
| POST | `/storage/` | admin | Create PVC |
| DELETE | `/storage/{name}` | admin | Delete PVC |
| GET | `/cronjobs/` | user | List CronJobs |
| PATCH | `/cronjobs/{name}/suspend` | admin | Suspend/resume CronJob |
| POST | `/cronjobs/{name}/trigger` | admin | Trigger CronJob now |
| GET | `/jobs/` | user | List batch Jobs |
| DELETE | `/jobs/{name}` | admin | Delete Job |
| GET | `/quotas/` | user | List ResourceQuotas |
| GET | `/helm/` | user | List Helm releases |
| GET | `/rbac/` | user | List Roles, ClusterRoles, Bindings |
| GET | `/objects/` | user | StatefulSets and DaemonSets |
| GET | `/prometheus/rules` | admin | List current Prometheus rules |
| POST | `/prometheus/rules` | admin | Create a new Prometheus alert rule; publishes via git commit/push, recreates Prometheus |
| PATCH | `/prometheus/rules/{group}/{alert}` | admin | Edit an existing alert rule |
| DELETE | `/prometheus/rules/{group}/{alert}` | admin | Delete an alert rule |

### HPA

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/workloads/{name}/hpa` | user | Get HPA for a workload |
| POST | `/workloads/{name}/hpa` | admin | Create or update HPA |
| DELETE | `/workloads/{name}/hpa` | admin | Delete HPA |

### Other

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | none | Liveness check |
| GET | `/alerts/` | user | Active Prometheus alerts (proxied) |
| GET | `/alert-history/` | user | Persisted alert firings — params: `limit`, `offset`, `severity`, `state` |
| GET | `/audit/` | user | Audit log — params: `limit`, `offset`, `status`, `resource_type` |
| POST | `/auth/login` | none | Exchange credentials for JWT; sets `pi_sso` cookie; triggers new-login-IP security alert if applicable |
| POST | `/auth/logout` | user | Clear session |
| POST | `/auth/refresh` | user | Refresh JWT token |
| GET | `/auth/me` | user | Current authenticated user |
| GET | `/auth/verify` | cookie | Validates `pi_sso` cookie — called by nginx `auth_request` for the household-services SSO gate, not called directly |
| GET | `/auth/wallabag-sso` | cookie | Auto-login bridge: logs the current user into Wallabag's shared account, redirects into the app |
| GET | `/auth/wallabag-sso-finish` | internal | Second hop of the Wallabag bridge handoff — reached only via redirect, not called directly |
| GET | `/auth/vikunja-sso` | cookie | Auto-login bridge: logs the current user into their own mapped Vikunja account, redirects into the app |
| GET | `/auth/vikunja-sso-finish` | internal | Second hop of the Vikunja bridge handoff — writes the access JWT into `localStorage` and redirects into the app |
| GET | `/users/` | admin | List users |
| POST | `/users/` | admin | Create user |
| DELETE | `/users/{id}` | admin | Delete user |
| GET | `/notifications/channels` | admin | List notification channels |
| POST | `/notifications/channels` | admin | Create notification channel — `channel_type` (`webhook`/`email`), `url` or `email_address`, `min_severity` (`warning`/`critical`, email only) |
| PATCH | `/notifications/channels/{id}` | admin | Update a channel (e.g. its `min_severity` threshold) |
| DELETE | `/notifications/channels/{id}` | admin | Delete notification channel |
| POST | `/notifications/channels/{id}/test` | admin | Send test notification |

---

## Service ports

| Service | Port | Access |
|---|---|---|
| nginx (single entry point) | 80 | LAN + public via Cloudflare Tunnel — platform hostnames, household-services SSO gate |
| React dashboard (Vite) | 5173 | LAN (proxied by nginx; not meant to be hit directly) |
| FastAPI backend | 8000 | LAN |
| Jenkins | 8080 | LAN |
| ArgoCD | 30443 | LAN (HTTPS, NodePort) |
| Grafana | 3000 | LAN |
| Prometheus | 9090 | LAN |
| AlertManager | 9093 | LAN |
| PostgreSQL | 5432 | internal only |
| Redis | 6379 | internal only |
| node-exporter | 9100 | internal (K3s pod network) |
| Traefik HTTP | 80 | K3s HostPort (all nodes) |
| Container registry | 5000 | LAN (no auth) |
| Loki | 3100 | internal only |
| Traefik HTTPS | 443 | K3s HostPort (all nodes) |
| Cloudflare Tunnel | outbound only | Public internet → pi-node1:80 |

---

## Test suite

The backend has a pytest suite covering all major API surfaces. Tests run against an in-process SQLite database (no external dependencies) with mocked K8s and SSH services.

```bash
cd backend
pytest --tb=long -x
```

Tests live in `backend/tests/` and cover: health, auth, nodes, workloads, namespaces, configmaps, storage, pods, jobs, quotas, audit, notification channels, rate limiting, retention, and WebSocket log routes (27 test files, 310 tests). `asyncio_mode = auto` via `pytest-asyncio`.

CI runs the test suite on every commit (both pipelines) and blocks deploy if any test fails.

---

## Development setup

```bash
# Backend
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

The backend requires PostgreSQL and Redis. Run them via Docker:

```bash
docker compose up -d postgres redis
```

Copy `.env.example` to `backend/.env` and fill in values:

```
DATABASE_URL=postgresql+asyncpg://pi_cluster:PASSWORD@localhost:5432/pi_cluster
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
K8S_KUBECONFIG_PATH=/path/to/kubeconfig
K8S_API_HOST=10.100.102.10
SSH_USERNAME=admin
SSH_PASSWORD=your-node-password
```

Start services:

```bash
# Backend (auto-reload)
cd backend && uvicorn app.main:app --reload --port 8000

# Frontend (Vite dev server)
cd frontend && npm run dev
```

API docs: `http://localhost:8000/docs`

---

## Deployment

Code is deployed automatically by Jenkins on every push to `master`. Manual steps are only needed for first-time setup or emergency hotfixes.

All Docker Compose services are configured with `restart: unless-stopped` — the platform stack starts automatically when the cluster is powered on.

> SSH to pi-node1 uses password authentication: `ssh admin@10.100.102.10`.

### Application path on pi-node1

All application code lives at `/home/admin/pi-cluster` on pi-node1. Jenkins rsyncs to this path. Docker Compose is run from there.

### First deploy

```bash
# On pi-node1 (as admin):
git clone https://github.com/AlexBoyev/pi-cluster /home/admin/pi-cluster
cd /home/admin/pi-cluster
cp .env.example .env   # fill in secrets
docker compose up -d
docker compose exec backend alembic upgrade head
```

### Manual backend hotfix (bypassing Jenkins)

`admin` already owns `/home/admin/pi-cluster` for files it wrote itself, but Jenkins' rsync runs as root and leaves whatever it touches root-owned — no chown needed unless you're editing a file Jenkins last wrote.

```bash
# Copy the changed files
scp backend/app/services/my_service.py admin@10.100.102.10:/home/admin/pi-cluster/backend/app/services/

# Restart the backend container
ssh admin@10.100.102.10 "cd /home/admin/pi-cluster && echo 'admin' | sudo -S docker compose restart backend"
```

If a migration is included, run it after the restart:

```bash
ssh admin@10.100.102.10 "cd /home/admin/pi-cluster && docker compose exec backend alembic upgrade head"
```

### Deploy a workload via the dashboard

1. Log in at `http://10.100.102.10`
2. Navigate to **Workloads**
3. Fill in Name, Image, Replicas, and optionally Container Port, CPU/memory limits, health probe paths
4. Click **Deploy** — the backend creates a K8s Deployment (and Service + Traefik Ingress if a port is specified)
5. The workload appears in the table with live replica counts from K8s

---

## Security

- JWT tokens expire and are refreshed automatically by the frontend
- All mutating operations require admin role
- SSH credentials are held only in backend environment variables — never in the frontend or API responses
- Audit log records every workload and node operation with actor and timestamp
- Secrets are in `.env` — never committed to Git
- SSH to pi-node1 as `admin`: key-based for operators, password-based for the backend's own health-check client (`SSH_PASSWORD` in `.env`) — password auth is not disabled on this host
- `audit_logs` and resolved `alert_history` rows older than `LOG_RETENTION_DAYS` (default 90) are deleted daily by a background job — see `docs/architecture.md` §22
- Rate limited: 300 requests/minute per IP globally, 10/minute on `/auth/login` specifically (brute-force protection); the real client IP behind the Cloudflare Tunnel is read from `Cf-Connecting-Ip`, not the tunnel's own loopback connection — see `docs/decisions.md`
- The GitHub PAT used to publish alert-rule edits (below) is a fine-grained token scoped to Contents-write on this one repository only, held in `.env` and never written to git config

### Security alerts

A separate, never-muted notification path from the infra-alert pipeline above, for events where email must not be filtered:

- **New-login-IP detection**: every successful login checks the user's IP against `known_login_ips` (per-user history). An IP never seen before for that user fires an alert to every enabled notification channel — no severity threshold applies, since there's no lower-severity version of "someone may be accessing your account."
- **Severity-filtered infra alerts, email only**: Prometheus/AlertManager firings (the alerting rules table above) go to every `webhook` channel unfiltered, but to `email` channels only at or above that channel's own configurable severity threshold (`warning`/`critical`, set per-channel in the Notifications page). This exists specifically so routine infra noise (HighCPU, HighDisk, etc.) doesn't drown out a personal inbox the way it would a Slack channel — an explicit fix after the first version of email alerting shipped and immediately proved too noisy.
- **Delivery**: outbound email goes through a Brevo SMTP relay (`BREVO_SMTP_*` in `.env`), shared with Vikunja's own reminder mail under a distinct `alerts@` sender address.
- **Alert rules themselves are editable from the dashboard** (Alert Rules page, admin-only) — add, edit, and delete Prometheus rules without SSH; changes publish via a real `git commit`/`push` to this repository (see `docs/architecture.md` §25) and recreate the Prometheus container to pick them up.

---

## Infrastructure as Code

### Ansible — node provisioning

Ansible automates the full cluster lifecycle from a bare OS install to a running platform.

```bash
# Install Ansible collections
ansible-galaxy collection install -r ansible/requirements.yml

# 1. Bootstrap all nodes (packages, cgroups, swap off, UFW)
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/bootstrap.yml

# 2. Install K3s (server on pi-node1, agents on pi-node2/3/4)
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/k3s.yml

# 3. Install ArgoCD and apply k8s/apps manifests
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/argocd.yml

# 4. Deploy the Docker Compose platform stack on pi-node1
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/platform.yml

# 5. Set up nightly Postgres + K3s datastore backups to pi-node4
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/backup.yml
```

Sensitive values (DB password, JWT secret) are prompted at runtime — never stored in the repo.

### Terraform — Kubernetes resource management

Terraform manages the cluster's Kubernetes-level resources: namespaces, RBAC, and the ArgoCD Application via the Kubernetes and Helm providers.

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # fill in secrets
terraform init
terraform plan
terraform apply
```

State is stored locally in `terraform.tfstate` (gitignored). The kubeconfig must be accessible at the path set in `kubeconfig_path`.

### Helm — platform chart

A Helm chart packages the full pi-cluster platform (backend, frontend, PostgreSQL, Redis) for deployment to K3s.

```bash
# Render templates to inspect output
helm template pi-cluster helm/pi-cluster/ \
  --set secrets.dbPassword=... \
  --set secrets.redisPassword=... \
  --set secrets.jwtSecret=...

# Install to K3s
helm upgrade --install pi-cluster helm/pi-cluster/ \
  --namespace pi-cluster --create-namespace \
  --set secrets.dbPassword=... \
  --set secrets.redisPassword=... \
  --set secrets.jwtSecret=...
```

---

## Repository layout

```
pi-cluster/
├── ansible/
│   ├── inventory/hosts.ini     ← real node IPs
│   ├── group_vars/all.yml      ← shared variables (no secrets)
│   ├── playbooks/              ← bootstrap, k3s, argocd, platform
│   └── roles/                  ← common, k3s_server, k3s_agent, platform
├── helm/
│   └── pi-cluster/
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/          ← backend, frontend, postgres, redis, ingress
├── terraform/
│   ├── providers.tf            ← kubernetes + helm providers
│   ├── main.tf                 ← namespaces, RBAC ClusterRole/Binding
│   ├── argocd.tf               ← ArgoCD helm release + Application manifest
│   ├── variables.tf
│   ├── outputs.tf
│   └── terraform.tfvars.example
├── backend/
│   ├── app/
│   │   ├── api/v1/         ← FastAPI routers (no business logic)
│   │   ├── services/       ← business logic, K8s, SSH, audit
│   │   ├── repositories/   ← SQLAlchemy DB access
│   │   ├── models/         ← ORM models
│   │   ├── schemas/        ← Pydantic request/response types
│   │   └── auth/           ← JWT, dependencies
│   ├── alembic/versions/   ← DB migrations (0001–0013)
│   └── tests/              ← pytest suite (27 files, 310 tests)
├── frontend/
│   └── src/
│       ├── pages/          ← full-page views (incl. AlertRulesPage, NotificationsPage)
│       ├── components/     ← modals, panels, shared UI
│       ├── api/            ← typed fetch wrappers
│       └── types/          ← TypeScript interfaces
├── k8s/
│   ├── apps/                ← ArgoCD watches this directory only
│   │   ├── node-exporter.yaml
│   │   ├── promtail.yaml
│   │   ├── kube-state-metrics.yaml
│   │   ├── wallabag/         ← household service: namespace, PVC, ConfigMap, Deployment, Service, Ingress, README
│   │   └── vikunja/          ← same pattern as wallabag/
│   └── traefik/              ← NOT ArgoCD-managed, see docs/architecture.md §13
├── nginx/
│   └── nginx.conf           ← platform hostnames, SSO gate, household-services wildcard fallback
├── prometheus/
│   ├── prometheus.yml
│   └── alerts.yml            ← editable from the dashboard's Alert Rules page, see docs/architecture.md §25
├── alertmanager/
│   └── alertmanager.yml
├── grafana/dashboards/
│   └── pi-cluster.json
├── docs/
│   ├── architecture.md
│   ├── roadmap.md
│   ├── decisions.md
│   └── operations.md        ← day-to-day runbooks: household services, node drain impact
├── docker-compose.yml
├── Jenkinsfile              ← post-merge: build + test + deploy
└── Jenkinsfile.test         ← pre-merge: build + test only
```
