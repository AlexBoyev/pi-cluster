# Architecture Decisions

## FastAPI for the backend

Chosen over Flask and Django REST Framework.

FastAPI provides native async support, automatic OpenAPI documentation, and first-class Pydantic integration. The cluster monitoring workload is I/O-bound (SSH, database, HTTP), which benefits from async throughout.

## PostgreSQL for persistent state

Chosen over SQLite.

PostgreSQL supports concurrent async connections via asyncpg, proper transactions, and the reliability expected from a control plane. SQLite has no async driver and serialises all writes.

## Layered architecture: API → Services → Repositories → Database

Business logic lives in services. Data access lives in repositories. HTTP concerns stay in routes.

This keeps services independently testable and prevents database queries from appearing in routes or business logic from appearing in repositories.

## Vite for frontend build tooling

Chosen over Create React App.

CRA is unmaintained. Vite provides fast HMR, a minimal configuration surface, and first-class TypeScript support. The project uses TypeScript strict mode throughout.

## pi-node1 as dedicated control plane

pi-node1 (10.100.102.10) runs the full platform stack via Docker Compose. The other three nodes run only the K3s agent and user workloads.

Keeping the control plane on a dedicated node avoids resource contention with scheduled workloads and gives a stable host for the database and monitoring stack.

## SSH for initial node metrics (replaced by node-exporter)

SSH was used initially for health metrics (CPU, RAM, disk, temp, uptime) because it requires no changes to the Pi nodes at bootstrap.

node-exporter (Phase 10) replaced SSH as the primary metrics source for Prometheus and Grafana. SSH is retained for node health card status (ONLINE/OFFLINE/DEGRADED/UNKNOWN) on the dashboard.

## K3s for Kubernetes orchestration

Chosen over full Kubernetes and over Docker Compose-only orchestration.

K3s is a lightweight, production-grade Kubernetes distribution designed for ARM/edge devices. It runs comfortably on Raspberry Pi hardware with a single-binary install. Using the full Kubernetes Python client means the platform can express the complete K8s API surface (Deployments, Services, Ingresses, probes, resource limits, eviction, etc.) without custom scheduling logic.

## ArgoCD for GitOps delivery of K8s manifests

ArgoCD watches `k8s/apps/` in the GitHub repository and applies changes automatically. This keeps cluster infrastructure (DaemonSets, RBAC) in Git with automatic reconciliation. No manual `kubectl apply` is needed for resources under `k8s/apps/`.

ArgoCD does not replace Jenkins — Jenkins owns Docker Compose deployment (backend, DB, monitoring stack). ArgoCD owns only K8s manifests.

## Jenkins for CI/CD

Jenkins replaced the initial rsync+SSH manual deploy script.

Jenkins runs on pi-node1 (`:8080`) with direct LAN access. It polls GitHub every 2 minutes and runs the full pipeline (rsync, docker compose build, alembic migrate, health check) on every push to `master`. This gave fully automated delivery without requiring external CI services.

## Traefik as the K8s ingress controller

Traefik was chosen because it has a lightweight DaemonSet mode, native Kubernetes Ingress support, and built-in TLS termination without requiring cert-manager. It runs as a DaemonSet binding HostPort 80/443, meaning any node IP can route to any workload.

The alternative (NodePort Services per workload) would expose a different port per service and require clients to know port numbers. Ingress with a consistent host (`<name>.pi-cluster.local`) is cleaner.

## node-exporter DaemonSet via ArgoCD

node-exporter is deployed as a K8s DaemonSet (one pod per node) managed by ArgoCD, rather than as a Docker Compose service on pi-node1 only.

This gives real per-node metrics from all four nodes without manual installation on each Pi. The DaemonSet is defined declaratively in `k8s/apps/node-exporter.yaml` and self-heals if a pod is evicted.

## Audit logging with best-effort semantics

The `AuditService` wraps all writes with `try/except` — a failed audit write never blocks or rolls back the underlying operation.

The audit log is a non-repudiation trail, not a transaction log. Losing one entry is far less harmful than failing a legitimate workload deploy because the audit write timed out. This also avoids deadlocks between the audit write and the main operation in the same DB session.

## Server-side audit filtering (not client-side)

The `GET /api/v1/audit` endpoint accepts `status` and `resource_type` query parameters and applies SQLAlchemy `where` clauses before paginating.

Client-side filtering only works against the currently loaded page, so filtering by `status=failure` would miss failures outside the current 50-record window. Server-side filtering is accurate against the full log.

## SSH key auth for pi-node1 (password auth disabled)

All access to pi-node1 uses SSH key authentication (`alex@10.100.102.10`). Password auth is disabled on the Pi's SSH daemon.

This is required because Jenkins, manual deploys, and SCP all use key-based auth. The implication: SSH or SCP commands in any shell (local or CI) require the key to be loaded (`ssh-add`) or configured in `~/.ssh/config`.

## /opt/pi-cluster as the application root

Application code on pi-node1 lives at `/opt/pi-cluster`. Jenkins rsyncs to this path; Docker Compose is run from there.

The initial deploy used `/home/admin/pi-cluster` but this was moved to `/opt` to follow Linux convention for optional application software and to separate platform code from user home directories. All scripts, documentation, and deployment instructions use `/opt/pi-cluster`.
