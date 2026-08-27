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

The project is currently in the architecture/foundation stage.

The initial implementation will focus on:

1. Cluster inventory
2. Node health
3. SSH-based metrics collection
4. Backend API
5. Web dashboard
6. Prometheus
7. Grafana

Orchestration, scheduling, deployments, and load balancing will be implemented later.

## Security

Credentials and secrets must never be committed to Git.

Local secrets are stored in `.env`.

Use `.env.example` as the template for required environment variables.
