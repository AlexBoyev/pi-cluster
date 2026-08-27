# Pi-Cluster

## Purpose

Pi-Cluster is a DevOps platform for managing and monitoring a Raspberry Pi cluster.

Current priority:

Cluster monitoring and management.

Future:

Orchestration, workload scheduling, deployments, and load balancing.

Do not implement future features prematurely.

## Stack

* Frontend: React + TypeScript
* Backend: Python + FastAPI
* Persistent data: PostgreSQL
* Cache / locks / ephemeral state: Redis
* Metrics: Prometheus
* Visualization: Grafana

## Architecture

Keep responsibilities separated:

API → Services → Repositories → Database

Do not place business logic or database queries in API routes.

Do not create monolithic frontend components.

## Security

* Never hardcode secrets or credentials.
* Never expose SSH credentials to the frontend.
* Never log passwords, tokens, or secrets.
* Do not expose arbitrary shell command execution through the API.
* Use `.env` for local secrets and keep it out of Git.

## Infrastructure

The current cluster inventory and architecture are documented in `docs/architecture.md`.

Do not hardcode infrastructure details in frontend components.

## Development Rules

* Inspect existing code before modifying it.
* Preserve working code unless there is a clear reason to change it.
* Make incremental changes.
* Do not rewrite unrelated code.
* Avoid unnecessary abstractions and dependencies.
* Use type hints in Python and strict TypeScript.
* Keep services independently testable.
* Handle node failures without breaking the entire dashboard.

## Current Priority

Build in this order:

1. Cluster and node inventory
2. Node health and metrics
3. Backend API
4. Dashboard UI
5. Prometheus and Grafana
6. Authentication
7. Orchestration

## Documentation

Keep documentation updated when architecture changes:

* `README.md`
* `docs/architecture.md`
* `docs/roadmap.md`
* `docs/decisions.md`
