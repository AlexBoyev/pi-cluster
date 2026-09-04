# Pi-Cluster

A self-hosted DevOps platform for a 4-node Raspberry Pi cluster. Provides a React dashboard for deploying, monitoring, and managing containerised workloads on Kubernetes, with a full CI/CD pipeline, GitOps delivery, Prometheus metrics, audit logging, SSH terminal, and live log streaming — all running on the cluster itself.

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
| DNS          | dnsmasq                           | LAN wildcard DNS + split-horizon for public domain |
| Tunnel       | Cloudflare Tunnel (cloudflared)   | Public access without port forwarding        |
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
  from GitHub     pi-node1        backend image   (32 tests)      --build       upgrade head
```

| Stage | What it does |
|---|---|
| **Checkout** | Clones `master` from GitHub into the Jenkins workspace |
| **Sync** | `rsync` copies the workspace to `/home/admin/pi-cluster` on pi-node1 |
| **Build** | `docker compose build backend` — builds the backend image |
| **Test** | `pytest` against all 32 tests using an in-process SQLite DB |
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
  users              ingress_host
  ─────              env_vars (JSON)         alert_history
  id                 cpu_limit               ─────────────
  username           memory_limit            id
  hashed_password    liveness_path           alert_name
  role               readiness_path          severity
                     status                  node_name
  notification_      created_at              instance
  channels                                   summary
  ────────────       * live from K8s,        labels (JSON)
  id                   not stored            fired_at
  name                                       resolved_at
  type (slack/email)
  config (JSON)
  enabled
```

Migrations: `alembic/versions/` — 0001 through 0010.

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
| GET | `/prom-rules/` | user | List current Prometheus rules |

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
| POST | `/auth/login` | none | Exchange credentials for JWT |
| POST | `/auth/refresh` | user | Refresh JWT token |
| GET | `/users/` | admin | List users |
| POST | `/users/` | admin | Create user |
| DELETE | `/users/{id}` | admin | Delete user |
| GET | `/notifications/` | admin | List notification channels |
| POST | `/notifications/` | admin | Create notification channel |
| DELETE | `/notifications/{id}` | admin | Delete notification channel |
| POST | `/notifications/{id}/test` | admin | Send test notification |

---

## Service ports

| Service | Port | Access |
|---|---|---|
| React dashboard | 80 | LAN |
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

Tests live in `backend/tests/` and cover: health, auth, nodes, workloads, namespaces, configmaps, storage, pods, jobs, quotas, audit, and WebSocket log routes (23 test files, 304 tests). `asyncio_mode = auto` via `pytest-asyncio`.

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
# On pi-node1 (as alex):
git clone https://github.com/AlexBoyev/pi-cluster /home/admin/pi-cluster
cd /home/admin/pi-cluster
cp .env.example .env   # fill in secrets
docker compose up -d
docker compose exec backend alembic upgrade head
```

### Manual backend hotfix (bypassing Jenkins)

```bash
# Ensure files are writable (Jenkins rsync runs as root, chown first)
ssh alex@10.100.102.10 "sudo chown -R alex:alex /home/admin/pi-cluster/backend"

# Copy the changed files
scp backend/app/services/my_service.py alex@10.100.102.10:/home/admin/pi-cluster/backend/app/services/

# Restart the backend container
ssh alex@10.100.102.10 "cd /home/admin/pi-cluster && docker compose restart backend"
```

If a migration is included, run it after the restart:

```bash
ssh alex@10.100.102.10 "cd /home/admin/pi-cluster && docker compose exec backend alembic upgrade head"
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
- SSH key auth is required for access to pi-node1; password auth is disabled
- `audit_logs` and resolved `alert_history` rows older than `LOG_RETENTION_DAYS` (default 90) are deleted daily by a background job — see `docs/architecture.md` §22

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
│   ├── alembic/versions/   ← DB migrations (0001–0010)
│   └── tests/              ← pytest suite (14 files, 32+ tests)
├── frontend/
│   └── src/
│       ├── pages/          ← full-page views
│       ├── components/     ← modals, panels, shared UI
│       ├── api/            ← typed fetch wrappers
│       └── types/          ← TypeScript interfaces
├── k8s/
│   └── apps/               ← ArgoCD watches this directory only
│       ├── node-exporter.yaml
│       └── traefik.yaml
├── prometheus/
│   ├── prometheus.yml
│   └── alerts.yml
├── alertmanager/
│   └── alertmanager.yml
├── grafana/dashboards/
│   └── pi-cluster.json
├── docs/
│   ├── architecture.md
│   ├── roadmap.md
│   └── decisions.md
├── docker-compose.yml
├── Jenkinsfile              ← post-merge: build + test + deploy
└── Jenkinsfile.test         ← pre-merge: build + test only
```
