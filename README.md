# Pi-Cluster

A self-hosted DevOps platform for a 4-node Raspberry Pi cluster. Provides a React dashboard for deploying, monitoring, and managing containerised workloads on Kubernetes, with a full CI/CD pipeline, GitOps delivery, Prometheus metrics, and audit logging — all running on the cluster itself.

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
  │  │ :80/:443 │  │  *.pi-cluster.local  │  │
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
| CI           | Jenkins                           | Build, migrate, deploy on every git push     |
| Orchestration| K3s (Kubernetes)                  | Container scheduling across 4 nodes          |
| GitOps       | ArgoCD                            | Declarative K8s manifest delivery            |
| Ingress      | Traefik DaemonSet                 | HTTP/S routing + TLS for workloads           |
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

Jenkins is the **continuous delivery engine**. Every push to `master` is detected via SCM polling (every 2 minutes) and the pipeline runs automatically.

### Pipeline stages

```
  ┌───────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐   ┌──────────────┐
  │ Checkout  │──▶│   Sync   │──▶│  Deploy  │──▶│ Migrate │──▶│ Health Check │
  └───────────┘   └──────────┘   └──────────┘   └─────────┘   └──────────────┘
  Clone repo      rsync to        docker compose  alembic        curl /health
  from GitHub     pi-node1        up --build      upgrade head
```

| Stage | What it does |
|---|---|
| **Checkout** | Clones `master` from GitHub into the Jenkins workspace |
| **Sync** | `rsync` copies the workspace to `/opt/pi-cluster` on pi-node1 |
| **Deploy** | `docker compose up -d --build backend frontend` — rebuilds and restarts containers |
| **Migrate** | Waits 5 s, then runs `alembic upgrade head` inside the backend container |
| **Health Check** | Waits 10 s, then `curl -sf http://10.100.102.10:8000/health` |

Jenkins runs as a Docker service on pi-node1 (`:8080`) with direct LAN access to the cluster.

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

- **SYNC STATUS: Synced** → cluster matches what is in `k8s/apps/` at HEAD. This is the signal you want.
- **Last Sync commit** shows the last commit that changed a file inside `k8s/apps/`. If recent commits only changed `backend/` or `frontend/`, ArgoCD has nothing new to apply — "Synced to HEAD" is correct and expected.

---

## Workload lifecycle

```
  Deploy ──▶ Scale ──▶ Update image ──▶ Set env vars ──▶ Set resource limits ──▶ Delete
     │                                                                                │
     ├──▶ Configure health probes (liveness + readiness HTTP)                        │
     │                                                                                │
     ├──▶ Rolling restart (restartedAt annotation patch)                             │
     │                                                                                │
     ├──▶ Drain node (cordon + evict all pods)                                       │
     │                                                                                │
     ├──▶ View pod list (phase, ready count, node, IP, age)                          │
     │                                                                                │
     ├──▶ View pod logs (live, last N lines)                                         │
     │                                                                                │
     └──▶ View K8s events (Warning/Normal, age-sorted)
```

Every operation:
- Uses the Kubernetes Python client against the K3s API on pi-node1
- Updates the PostgreSQL workload record to keep the DB in sync
- Is audit-logged with actor, timestamp, result, and detail
- Triggers a K8s rolling restart where applicable (image, env, resources, probes)

The workloads table auto-refreshes every 15 seconds. Polling pauses while any modal is open.

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
  ─────              env_vars (JSONB)        alert_history
  id                 cpu_limit               ─────────────
  username           memory_limit            id
  hashed_password    liveness_path           alert_name
  role               readiness_path          severity
                     status                  node_name
                     created_at              instance
                                             summary
                     * live from K8s,        labels (JSON)
                       not stored            fired_at
                                             resolved_at
```

Migrations: `alembic/versions/` — 0001 through 0009.

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
| GET | `/workloads/{name}/pods` | user | List pods with phase, ready count, node, IP |
| GET | `/workloads/{name}/metrics` | user | Live CPU/memory usage from Prometheus |
| GET | `/workloads/{name}/logs` | user | Last N pod log lines |
| GET | `/workloads/{name}/events` | user | K8s events for workload and its pods |
| DELETE | `/workloads/{name}` | admin | Delete deployment, service, and ingress |
| POST | `/workloads/nodes/{name}/cordon` | admin | Mark node unschedulable |
| DELETE | `/workloads/nodes/{name}/cordon` | admin | Mark node schedulable |
| POST | `/workloads/nodes/{name}/drain` | admin | Cordon + evict all non-DaemonSet pods |

### Other

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | none | Liveness check |
| GET | `/nodes/` | user | Cluster node inventory |
| GET | `/nodes/{id}/health` | user | SSH-based health metrics (CPU, RAM, disk, temp) |
| GET | `/alerts/` | user | Active Prometheus alerts (proxied) |
| GET | `/alert-history/` | user | Persisted alert firings — params: `limit`, `offset`, `severity`, `state` |
| GET | `/audit/` | user | Audit log — params: `limit`, `offset`, `status`, `resource_type` |
| GET | `/cluster/capacity` | user | Cluster-wide CPU/memory: allocatable, requested, and actually used (Prometheus) |
| GET | `/events/` | user | K8s events across all namespaces — params: `namespace`, `event_type`, `limit` |
| GET | `/namespaces/` | user | List all K8s namespaces with status and labels |
| POST | `/namespaces/` | admin | Create namespace (protected namespaces blocked) |
| DELETE | `/namespaces/{name}` | admin | Delete namespace (protected namespaces blocked) |
| POST | `/auth/login` | none | Exchange credentials for JWT |
| POST | `/auth/refresh` | user | Refresh JWT token |

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
| Traefik HTTPS | 443 | K3s HostPort (all nodes) |

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

> **SSH key requirement:** All SSH-based operations to pi-node1 (manual deploys, SCP) require key-based authentication. Password auth is disabled. Your SSH key must be loaded in the shell (`ssh-add`) before running any `ssh` or `scp` commands to `alex@10.100.102.10`.

### Application path on pi-node1

All application code lives at `/opt/pi-cluster` on pi-node1. Jenkins rsyncs to this path. Docker Compose is run from there.

### First deploy

```bash
# On pi-node1 (as alex):
git clone https://github.com/AlexBoyev/pi-cluster /opt/pi-cluster
cd /opt/pi-cluster
cp .env.example .env   # fill in secrets
docker compose up -d
docker compose exec backend alembic upgrade head
```

### Manual backend hotfix (bypassing Jenkins)

```bash
# Ensure files are writable (Jenkins rsync runs as root, chown first)
ssh alex@10.100.102.10 "sudo chown -R alex:alex /opt/pi-cluster/backend"

# Copy the changed files
scp backend/app/services/my_service.py alex@10.100.102.10:/opt/pi-cluster/backend/app/services/

# Restart the backend container
ssh alex@10.100.102.10 "cd /opt/pi-cluster && docker compose restart backend"
```

If a migration is included, run it after the restart:

```bash
ssh alex@10.100.102.10 "cd /opt/pi-cluster && docker compose exec backend alembic upgrade head"
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
│   └── alembic/versions/   ← DB migrations (0001–0008)
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
└── Jenkinsfile
```
