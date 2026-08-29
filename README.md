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
- **pi-node1** runs the entire platform stack via Docker Compose (backend, database, monitoring, CI)
- **pi-node2/3/4** run K3s agent and receive scheduled workloads

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
    │ SCM poll (2 min)          │ webhook (future)
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
  ┌──────────────────────────────────────┐
  │           K3s Cluster                │
  │                                      │
  │  ┌──────────┐  ┌──────────────────┐  │
  │  │  ArgoCD  │  │ node-exporter    │  │
  │  │          │  │ DaemonSet        │  │
  │  └──────────┘  └──────────────────┘  │
  │                                      │
  │  ┌──────────┐  ┌──────────────────┐  │
  │  │ Traefik  │  │  User workloads  │  │
  │  │ Ingress  │  │  (Deployments)   │  │
  │  └──────────┘  └──────────────────┘  │
  │                                      │
  │  pi-node1 ── pi-node2 ── pi-node3 ── pi-node4
  └──────────────────────────────────────┘
```

---

## Stack

| Layer        | Technology                        | Purpose                                      |
|--------------|-----------------------------------|----------------------------------------------|
| Frontend     | React + TypeScript + Vite         | Dashboard UI                                 |
| Backend      | Python + FastAPI + SQLAlchemy     | REST API, business logic, K8s control        |
| Database     | PostgreSQL                        | Persistent state (nodes, workloads, audit)   |
| Cache        | Redis                             | Health cache (90s TTL), distributed locks    |
| Metrics      | Prometheus + node-exporter        | Time-series metrics from all nodes           |
| Dashboards   | Grafana                           | Metric visualisation, 10 panels              |
| Alerting     | Prometheus rules + AlertManager   | NodeDown/HighCPU/RAM/Disk/Temp rules         |
| CI           | Jenkins                           | Build, migrate, deploy on every git push     |
| Orchestration| K3s (Kubernetes)                  | Container scheduling across 4 nodes          |
| GitOps       | ArgoCD                            | Declarative K8s manifest delivery            |
| Ingress      | Traefik                           | HTTP/S routing + TLS for workloads           |

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

### What Jenkins does

Jenkins is the **continuous delivery engine**. Every time code is pushed to `master` on GitHub, Jenkins detects it (via SCM polling every 2 minutes), runs the pipeline, and the new version is live on the cluster within ~2 minutes of the poll firing.

### Pipeline stages

The pipeline is defined in `Jenkinsfile` as a declarative pipeline with five named stages. In Jenkins, navigate to the build → **Pipeline Steps** or use the **Stage View** (requires the *Pipeline Stage View* plugin) to see the visual block workflow:

```
  ┌───────────┐   ┌──────────┐   ┌──────────┐   ┌─────────┐   ┌──────────────┐
  │ Checkout  │──▶│   Sync   │──▶│  Deploy  │──▶│ Migrate │──▶│ Health Check │
  └───────────┘   └──────────┘   └──────────┘   └─────────┘   └──────────────┘
  Clone repo      rsync to        docker compose  alembic        curl /health
  from GitHub     pi-node1        up --build      upgrade head
```

**Stage details:**

| Stage | What it does |
|---|---|
| **Checkout** | Clones the `master` branch from GitHub into the Jenkins workspace |
| **Sync** | `rsync` copies the workspace to `/home/admin/pi-cluster` on pi-node1, excluding `.git`, `.env`, `__pycache__`, `node_modules` |
| **Deploy** | `docker compose up -d --build backend frontend` — rebuilds both containers from the updated source and starts them |
| **Migrate** | Waits 5 s for the backend to start, then runs `alembic upgrade head` inside the backend container to apply any pending DB migrations |
| **Health Check** | Waits 10 s, then `curl -sf http://10.100.102.10:8000/health` — if it fails, the build is marked FAILED |

> **Tip — Stage View plugin:** To see the green square workflow instead of a console log list, install the **Pipeline Stage View** plugin in Jenkins (`Manage Jenkins → Plugins → Available`). Alternatively, install **Blue Ocean** for a full pipeline visualisation UI at `:8080/blue`.

### Why Jenkins runs on the cluster

Jenkins runs as a Docker service on pi-node1 (`:8080`) so it has direct LAN access to run `rsync`, `docker compose`, and `alembic` without needing external network tunnels. It is not exposed to the internet.

---

## GitOps — ArgoCD

### What ArgoCD does

ArgoCD is the **Kubernetes manifest delivery system**. It watches the `k8s/apps/` directory in this Git repository and automatically applies any changes to the K3s cluster. When a new manifest is pushed (or an existing one changes), ArgoCD detects it within ~3 minutes and reconciles the cluster state.

### Scope

ArgoCD **only manages what is inside `k8s/apps/`**:

```
k8s/
└── apps/
    ├── node-exporter.yaml    ← prometheus/node-exporter DaemonSet (all 4 nodes)
    └── traefik.yaml          ← Traefik DaemonSet + RBAC
```

Everything else (backend, frontend, PostgreSQL, Redis, Prometheus, Grafana, AlertManager) is managed by **Docker Compose** via Jenkins — ArgoCD does not touch those.

### ArgoCD vs Jenkins — who does what

```
  git push
     │
     ├──▶ Jenkins polls GitHub
     │         │
     │         ▼
     │    k8s/apps/ changed?
     │         │ no  ──▶ Jenkins deploys Docker Compose stack
     │         │ yes ──▶ ArgoCD detects k8s/apps/ change → applies manifests
     │
     └──▶ ArgoCD polls GitHub (independent, ~3 min)
               │
               ▼
          k8s/apps/ changed? → apply to K3s cluster
```

### Reading the ArgoCD UI

- **SYNC STATUS: Synced** → cluster matches what is in `k8s/apps/` in Git. This is the signal you care about.
- **APP HEALTH: Healthy** → all managed resources are running correctly.
- **Last Sync commit message** shows the last commit that actually changed a file inside `k8s/apps/`. If the latest commits only changed `backend/` or `frontend/`, ArgoCD has nothing to do — "Synced to HEAD" means it has already processed all relevant changes.

Example: if the last change to `k8s/apps/` was the Phase 10 node-exporter commit, ArgoCD will report that commit message even though the project is now on Phase 16. This is correct and expected — ArgoCD is fully up to date.

---

## pi-cluster-deploy (ArgoCD Application)

The ArgoCD Application named `pi-cluster` (or `pi-cluster-deploy`) is the object that tells ArgoCD what to watch and where to apply it. Its configuration:

```yaml
source:
  repoURL: https://github.com/AlexBoyev/pi-cluster
  targetRevision: HEAD
  path: k8s/apps

destination:
  server: https://kubernetes.default.svc
  namespace: monitoring          # node-exporter goes here
                                 # traefik goes to kube-system via its own manifest

syncPolicy:
  automated:
    prune: true      # delete resources removed from Git
    selfHeal: true   # re-apply if someone manually changes K8s state
```

**In plain English:** "Watch `k8s/apps/` on `master`. Whenever it changes, apply all YAML files inside it to the local K3s cluster. If someone manually deletes or edits a resource, put it back."

This means you can manage cluster infrastructure (DaemonSets, RBAC, namespaces) purely through Git — no `kubectl apply` needed.

---

## Workload lifecycle

The platform manages the full lifecycle of containerised workloads on K3s:

```
  Deploy ──▶ Scale ──▶ Update image ──▶ Set env vars ──▶ Set resource limits ──▶ Delete
     │                                                                                │
     ├──▶ Configure health probes (liveness + readiness HTTP)                        │
     │                                                                                │
     ├──▶ Rolling restart (restartedAt annotation patch)                             │
     │                                                                                │
     ├──▶ View pod logs (live, last N lines)                                         │
     │                                                                                │
     ├──▶ View K8s events (Warning/Normal, age-sorted)                               │
     │                                                                                │
     └──▶  Cordon node (stop scheduling)  ──▶  Uncordon
```

Each operation:
- Is performed via the FastAPI backend using the Kubernetes Python client against the K3s API
- Updates the PostgreSQL workload record to keep the database in sync
- Is audit-logged with the actor's username, timestamp, result, and detail
- Triggers a K8s rolling restart where applicable (image, env vars, resource limits, probes)

The workloads table auto-refreshes every 15 seconds. The Live indicator pulses green and switches to "Paused" while any modal is open.

---

## Monitoring stack

```
  pi-node1/2/3/4
       │
  node-exporter (DaemonSet, port 9100)
       │  scrape every 15s
       ▼
  Prometheus (:9090)
       │                    │
       │ evaluate rules      │ query
       ▼                    ▼
  AlertManager (:9093)   Grafana (:3000)
       │                    │
       │ group/throttle      │ 10 dashboard panels:
       ▼                    │   CPU % per node
  Backend /api/v1/alerts   │   RAM % per node
       │                    │   Disk % per node
       ▼                    │   Temperature per node
  AlertsPanel              │   Network Rx/Tx per node
  (Dashboard)              └──────────────────────────
```

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
  ─────              env_vars (JSONB)
  id                 cpu_limit
  username           memory_limit
  hashed_password    liveness_path
  role               readiness_path
                     status
                     created_at

                     * live from K8s, not stored
```

---

## API reference

All routes are prefixed `/api/v1/`. Authentication is JWT Bearer token.

### Workloads

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/workloads/` | user | List all non-deleted workloads |
| POST | `/workloads/` | admin | Deploy new workload |
| PATCH | `/workloads/{name}/scale` | admin | Set replica count (1–10) |
| PATCH | `/workloads/{name}/image` | admin | Rolling image update |
| PATCH | `/workloads/{name}/env` | admin | Replace env vars (rolling restart) |
| PATCH | `/workloads/{name}/resources` | admin | Set CPU/memory limits (rolling patch) |
| PATCH | `/workloads/{name}/probes` | admin | Set liveness/readiness HTTP probe paths |
| POST | `/workloads/{name}/restart` | admin | Rolling restart (restartedAt annotation) |
| GET | `/workloads/{name}/logs` | user | Last N pod log lines |
| GET | `/workloads/{name}/events` | user | K8s events for workload + pods |
| DELETE | `/workloads/{name}` | admin | Delete deployment, service, ingress |
| GET | `/workloads/capacity` | user | Node CPU/RAM allocatable vs requested |
| POST | `/workloads/nodes/{name}/cordon` | admin | Mark node unschedulable |
| DELETE | `/workloads/nodes/{name}/cordon` | admin | Mark node schedulable |

### Other

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | none | Liveness check |
| GET | `/nodes/` | user | Cluster node inventory |
| GET | `/nodes/{id}/health` | user | SSH-based health metrics |
| GET | `/alerts/` | user | Active Prometheus alerts |
| GET | `/audit/` | user | Audit log (paginated) |
| POST | `/auth/login` | none | Get JWT token |
| POST | `/auth/refresh` | user | Refresh token |

---

## Service ports

| Service | Port | Access |
|---|---|---|
| React dashboard | 80 | LAN |
| FastAPI backend | 8000 | LAN |
| Jenkins | 8080 | LAN |
| ArgoCD | 30443 | LAN (HTTPS) |
| Grafana | 3000 | LAN |
| Prometheus | 9090 | LAN |
| AlertManager | 9093 | LAN |
| PostgreSQL | 5432 | internal |
| Redis | 6379 | internal |
| node-exporter | 9100 | internal (K3s) |

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

The backend needs PostgreSQL and Redis. The simplest approach is to run them via Docker:

```bash
docker compose up -d postgres redis
```

Copy `.env.example` to `backend/.env`:

```
DATABASE_URL=postgresql+asyncpg://pi_cluster:PASSWORD@localhost:5432/pi_cluster
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
K8S_KUBECONFIG_PATH=/path/to/kubeconfig
K8S_API_HOST=10.100.102.10
```

Then start the services:

```bash
# Backend (auto-reload)
cd backend && uvicorn app.main:app --reload --port 8000

# Frontend (Vite dev server)
cd frontend && npm run dev
```

API docs available at `http://localhost:8000/docs`.

---

## Deployment

Code is deployed automatically by Jenkins on every push to `master`. Manual steps are only needed for first-time setup or emergency hotfixes.

### First deploy

```bash
# On pi-node1:
git clone https://github.com/AlexBoyev/pi-cluster
cd pi-cluster
cp .env.example .env   # fill in secrets
docker compose up -d
docker compose exec backend alembic upgrade head
```

### Manual backend hotfix (bypassing Jenkins)

```bash
scp backend/app/services/my_service.py admin@10.100.102.10:/home/admin/pi-cluster/backend/app/services/
ssh admin@10.100.102.10 "cd /home/admin/pi-cluster && docker compose restart backend"
```

### Jenkins pipeline stages view

To see the green-squares stage visualisation instead of a flat console log:

1. In Jenkins, open the build page
2. Click **"Pipeline Steps"** in the left sidebar (built-in, always available)
3. For the full block diagram, install **Pipeline Stage View Plugin** via `Manage Jenkins → Plugins → Available → "Pipeline Stage View"`
4. For the best pipeline UI, install **Blue Ocean** and open `:8080/blue`

### Deploy a workload via the dashboard

1. Log in at `http://10.100.102.10`
2. Navigate to **Workloads**
3. Fill in Name, Image, Replicas, and optionally Container Port
4. Click **Deploy** — the backend creates a K8s Deployment (and Service + Ingress if a port was specified)
5. The workload appears in the table with live replica counts from K8s

---

## Security

- JWT tokens expire and are refreshed automatically
- All mutating operations require admin role
- SSH credentials are held only in backend environment variables — never in the frontend or API responses
- Audit log records every create, delete, scale, image update, env update, cordon/uncordon with actor and timestamp
- Secrets are in `.env` — never committed to Git

---

## Repository layout

```
pi-cluster/
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
│   └── apps/               ← ArgoCD watches this directory
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
