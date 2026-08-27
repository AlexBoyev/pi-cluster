# Pi-Cluster

Pi-Cluster is a DevOps and infrastructure management platform for managing a Raspberry Pi cluster.

The initial goal is to provide a clean dashboard for monitoring cluster nodes, network infrastructure, system resources, and node health.

The long-term goal is to evolve the platform into an infrastructure orchestration system capable of managing workloads, deployments, scheduling, service health, and load balancing.

## Current Cluster

| Node     | IP            |
| -------- | ------------- |
| pi-node1 | 10.100.102.10 |
| pi-node2 | 10.100.102.5  |
| pi-node3 | 10.100.102.17 |
| pi-node4 | 10.100.102.12 |

Network:

* Subnet: `10.100.102.0/24`
* Router: `10.100.102.1`
* Cluster switch: `10.100.102.200`

## Technology

* React + TypeScript
* FastAPI + Python
* PostgreSQL
* Redis
* Prometheus
* Grafana
* Docker / Docker Compose

## Architecture

See [`docs/architecture.md`](docs/architecture.md).

## Roadmap

See [`docs/roadmap.md`](docs/roadmap.md).

## Development

Code is written locally. The platform runs on the cluster.

### Local setup

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

### Running locally

The backend needs PostgreSQL and Redis. Tunnel the cluster's instances to localhost:

```bash
make tunnel   # keeps running — open a second terminal for the next steps
```

Copy `.env.example` to `backend/.env` and set:

```
DATABASE_URL=postgresql+asyncpg://pi_cluster:PASSWORD@localhost:5432/pi_cluster
REDIS_URL=redis://localhost:6379/0
```

Then start the services:

```bash
make dev-backend    # uvicorn with --reload on :8000
make dev-frontend   # vite dev server on :5173
```

API docs: http://localhost:8000/docs

## Deployment

The platform runs on **pi-node1 (10.100.102.10)** as the control plane via Docker Compose.

### First deploy

SSH into pi-node1 and ensure Docker is installed, then place a `.env` file in `~/pi-cluster/.env`.

### Deploy

```bash
make deploy
```

This rsyncs the project to pi-node1, rebuilds containers, and runs any pending migrations.

Orchestration, scheduling, deployments, and load balancing will be implemented later.

## Security

Credentials and secrets must never be committed to Git.

Local secrets are stored in `.env`.

Use `.env.example` as the template for required environment variables.
