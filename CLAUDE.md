# Pi-Cluster

## Purpose

Pi-Cluster is a DevOps platform for managing and monitoring a Raspberry Pi cluster.

Status (see `docs/roadmap.md` for the full phase-by-phase list — do not hardcode a phase count here, it goes stale immediately; the frontend sidebar's `Phase N` string is the freshest single indicator of how far the phase count has actually gone):

Cluster monitoring and management, orchestration, workload scheduling, deployments, load balancing, CI/CD, GitOps, backups, log aggregation, and a container registry are all built. This is a full K3s admin platform now, not just a monitoring dashboard — don't treat orchestration/scheduling/deployment work as "future" or out of scope.

Current priority:

Operational hardening — backup/DR, log aggregation, image registry, retention — rather than new dashboard features. Check `docs/roadmap.md` for what's actually still open before assuming a feature doesn't exist.

Do not implement future features prematurely.

## Stack

* Frontend: React + TypeScript
* Backend: Python + FastAPI
* Persistent data: PostgreSQL
* Cache / locks / ephemeral state / rate limiting: Redis (rate limiting is in-process in-memory, not Redis — see `docs/decisions.md`)
* Orchestration: K3s (single-server; embedded SQLite/kine datastore, not etcd)
* Ingress: Traefik (K3s DaemonSet)
* GitOps (K8s manifests only): ArgoCD
* CI/CD (Docker Compose stack): Jenkins
* Metrics: Prometheus + node-exporter + kube-state-metrics
* Log aggregation: Loki + Promtail
* Visualization: Grafana
* Container registry: `registry:2` (LAN only, no auth)
* Provisioning: Ansible (node bootstrap, K3s install, backups) + Terraform (K8s namespaces/RBAC/ArgoCD Application) + Helm (chart exists for a possible future K3s migration of the platform itself — not currently used for deployment)
* Local DNS: dnsmasq · Public ingress: Cloudflare Tunnel (`cloudflared`)

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

## Documentation

Keep documentation updated when architecture changes:

* `README.md`
* `docs/architecture.md`
* `docs/roadmap.md`
* `docs/decisions.md`
