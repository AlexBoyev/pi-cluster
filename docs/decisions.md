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

## Ansible for node provisioning, not cloud Terraform

The cluster is bare metal. There is no cloud provider API. Ansible is the right tool for configuring physical nodes — it connects via SSH and is idempotent. Terraform's cloud provisioning providers (AWS, GCP, etc.) do not apply here.

Terraform is used for the Kubernetes-level layer: namespaces, RBAC, and ArgoCD Application resources via the hashicorp/kubernetes and hashicorp/helm providers. This is the layer Terraform can actually manage declaratively against the K3s API.

## Helm chart targets K3s deployment, not Docker Compose replacement

The Helm chart (`helm/pi-cluster/`) packages the platform as K8s resources. The current production deployment runs Docker Compose on pi-node1 (managed by Jenkins). The Helm chart exists to support a future migration to running the platform itself inside K3s, and to demonstrate chart structure for the workloads the platform manages. It does not replace the current Docker Compose setup.

## Secrets never in repository

Ansible prompts for secrets at runtime. Terraform sensitive variables must be provided via `terraform.tfvars` (gitignored) or environment variables (`TF_VAR_*`). Helm secrets are passed with `--set` or a local values override file. No secret value is ever committed to the repository.

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

Traefik was chosen because it has a lightweight DaemonSet mode, native Kubernetes Ingress support, and built-in TLS termination without requiring cert-manager. It runs as a DaemonSet binding HostPort 80/443, meaning any node it's scheduled on can route to any workload — as of the pi-node1 exclusion below, that's pi-node2/3/4, not all four.

The alternative (NodePort Services per workload) would expose a different port per service and require clients to know port numbers. Ingress with a consistent host (`<name>.pi-cluster.local`) is cleaner.

## Traefik is excluded from pi-node1

Traefik's DaemonSet (`k8s/traefik/traefik.yaml`) originally tolerated the control-plane taint specifically so it would also run on pi-node1, giving true "any node routes anywhere" ingress. In practice this meant Traefik's hostPort 80/443 binding fought with Docker Compose's `nginx` service, which already binds those same host ports on pi-node1 for the platform's own subdomains. The result was a persistent crash-loop on that node's Traefik pod — discovered via an orphaned/misbehaving process burning real CPU for 10+ hours before being traced back to this conflict.

Fixed with a `nodeAffinity` excluding `kubernetes.io/hostname: pi-node1`, rather than removing the control-plane tolerations (kept in case a second control-plane node is ever added). Traefik now only runs on pi-node2/3/4 — sufficient for K8s workload ingress, since pi-node1's own routing was always nginx's job, not Traefik's.

**Discovered while deploying this fix: `k8s/traefik/traefik.yaml` is not GitOps-managed at all.** ArgoCD's Application only watches `k8s/apps` (`spec.source.path`) — confirmed via `kubectl get application pi-cluster -n argocd -o jsonpath='{.spec.source.path}'`. Despite architecture.md previously implying Traefik was ArgoCD-managed like node-exporter/promtail, it was applied manually once (Phase 8) and has been drifting from the repo ever since; pushing this fix to git alone did nothing, it had to be applied by hand (`kubectl apply -f k8s/traefik/traefik.yaml`). Worth moving this file into `k8s/apps/` so it's actually under GitOps like everything else there — not done yet, flagged as a follow-up rather than risked this late in an unrelated change.

**Also observed while applying the fix: individual Traefik pods got stuck `Terminating` past their grace period more than once during the rollout** (first pi-node1's old pod, then pi-node3's) — required `--grace-period=0 --force` to clear. This happened on nodes with no port conflict, so it's not fully explained by the pi-node1 root cause above; combined with all 4 pods' pre-existing high restart counts (8-12 each, including the 3 nodes that never had a port conflict), there may be a second, still-unidentified issue with how Traefik terminates on this cluster. Worth keeping an eye on via the new `PodCrashLooping`/`PodNotReady` alerts rather than considered closed.

## node-exporter DaemonSet via ArgoCD

node-exporter is deployed as a K8s DaemonSet (one pod per node) managed by ArgoCD, rather than as a Docker Compose service on pi-node1 only.

This gives real per-node metrics from all four nodes without manual installation on each Pi. The DaemonSet is defined declaratively in `k8s/apps/node-exporter.yaml` and self-heals if a pod is evicted.

## Audit logging with best-effort semantics

The `AuditService` wraps all writes with `try/except` — a failed audit write never blocks or rolls back the underlying operation.

The audit log is a non-repudiation trail, not a transaction log. Losing one entry is far less harmful than failing a legitimate workload deploy because the audit write timed out. This also avoids deadlocks between the audit write and the main operation in the same DB session.

## Server-side audit filtering (not client-side)

The `GET /api/v1/audit` endpoint accepts `status` and `resource_type` query parameters and applies SQLAlchemy `where` clauses before paginating.

Client-side filtering only works against the currently loaded page, so filtering by `status=failure` would miss failures outside the current 50-record window. Server-side filtering is accurate against the full log.

## SSH to pi-node1: `admin`, both key and password auth enabled

Operator/interactive SSH and Claude Code sessions use `admin@10.100.102.10`, key-based. The backend's own `SSHService` (health checks, node restart/shutdown, the in-app SSH terminal) authenticates as the same `admin` user but with a **password** (`SSH_PASSWORD` in `.env`) via paramiko — password auth is not disabled on this host, and this was previously documented incorrectly (docs asserted `alex` + key-only, which was never true in practice).

A separate `alex` identity exists only for Ansible-managed automation (`ansible_user: alex` in `ansible/group_vars/all.yml`) — a distinct credential from the one used for actual day-to-day operations, and untested/unverified as of this writing (see the `/opt/pi-cluster` entry below for the same pattern: an Ansible-declared value that never matched what's actually running).

## `/home/admin/pi-cluster` is the real application root, not `/opt/pi-cluster`

Jenkins rsyncs to and runs Docker Compose from `/home/admin/pi-cluster` — this has always been true of the actual deploy pipeline (`Jenkinsfile`'s `PROJECT_DIR`, and the Jenkins service's own bind mount in `docker-compose.yml`).

An earlier version of this document claimed the app had been moved to `/opt/pi-cluster` "to follow Linux convention." That move was never actually made in the live deploy path — only `ansible/roles/platform`'s `platform_dir` variable points at `/opt/pi-cluster`, and that role is a separate, rarely-used alternate provisioning path (see below), not what Jenkins runs. Docs described the aspiration, not the reality, for some time; corrected here.

## Polling-based alert history, not AlertManager webhook receiver

Alert history (Phase 30) is recorded by a background poller that queries Prometheus every 30 seconds, not by configuring AlertManager to POST to a receiver endpoint.

The webhook approach would require exposing an unauthenticated HTTP endpoint that AlertManager can reach, adding receiver configuration to `alertmanager.yml`, and handling webhook delivery retries. The poller approach requires no changes to AlertManager, works with the existing Prometheus API the platform already queries, and is self-contained in the backend lifespan.

The tradeoff is a ±30s recording lag for new firings and resolutions, which is acceptable for operational history. Sub-second precision is not needed for post-mortem analysis. If finer precision or push-based alerting to external systems is needed later, a webhook receiver can be added without replacing the poller.

## Backups target pi-node4, not a NAS or cloud storage

The cluster has no NAS or cloud storage account. Backups (Postgres dump + K3s datastore) are shipped nightly from pi-node1 to pi-node4 over a dedicated SSH key, via `ansible/roles/backup`.

This is a same-LAN, same-power-circuit copy — it protects against pi-node1's SD card/disk failing, but not against a whole-site event (power loss, theft, fire). That's a known, accepted gap for a homelab; revisit if off-site storage becomes available.

## K3s datastore backup is a SQLite `.backup`, not an etcd snapshot

pi-node1 runs K3s in single-server mode (`ansible/roles/k3s_server`) with no `--cluster-init` and no external datastore, so it uses the embedded SQLite (kine) datastore — not etcd. `k3s etcd-snapshot` does not apply here.

The backup script instead uses SQLite's own online backup command (`sqlite3 state.db ".backup ..."`), which produces a consistent copy without stopping k3s, plus a tarball of `/etc/rancher/k3s` and the server TLS directory (certs/tokens needed for a full restore). If the cluster is ever moved to multi-server HA (embedded etcd), this backup step needs to change to `k3s etcd-snapshot save`.

## Postgres backup reads via `docker exec`, not `docker compose exec`

Jenkins' rsync leaves `/home/admin/pi-cluster` root-owned on pi-node1 (a known recurring friction point). `docker compose exec` needs to resolve the compose project from that directory; `docker exec pi-cluster-postgres-1 pg_dump ...` targets the container directly by its known name and needs nothing but docker socket access, which `admin` already has (verified empirically — `docker ps`/`docker stats` work as `admin` with no `sudo`). This sidesteps the permission issue entirely instead of working around it. The backup role itself runs as `admin`, not `alex`, for the same reason — see the SSH entry above.

## Prometheus and AlertManager are LAN-restricted at nginx, not just "trusted by convention"

Both hostnames (`prometheus.*`, `alertmanager.*`) are proxied by the same nginx `server` block regardless of whether the request arrived via direct LAN access (`*.pi-cluster.lan`) or through the Cloudflare Tunnel (`*.cluster.download`) — nginx routes on the `Host` header only, it doesn't distinguish the two paths itself. Neither Prometheus nor AlertManager has any authentication of its own, unlike Grafana and Jenkins (both have a login).

Fixed with `allow 10.100.102.0/24; deny all;` on both server blocks, the same pattern already used for `/api/v1/vault`. This works correctly against tunnel traffic specifically because `cloudflared` runs with `network_mode: host` and forwards to nginx over `localhost` — tunnel-routed requests arrive at nginx as `127.0.0.1`, outside the allowed CIDR, so they're rejected; genuine direct-LAN requests keep their real source IP and pass. Verified against the live nginx binary (`nginx -t`) before rollout.

This was found by checking, not assumed: `cloudflared`'s actual tunnel routing rules live in Cloudflare's dashboard, not this repo, so it wasn't possible to confirm from code alone which hostnames the tunnel exposes. The nginx-level restriction is a repo-visible, defense-in-depth fix regardless of what the tunnel config turns out to be — but the Cloudflare Zero Trust dashboard should still be checked directly to confirm which routes exist and whether Cloudflare Access policies are (or should be) applied at the tunnel level too.

## Container registry has no authentication

`registry:2` is bound to pi-node1's LAN-facing port 5000 with no auth configured, matching the existing posture of Prometheus (`:9090`) and Postgres (`:5432`) — internal services trusted on the home LAN rather than hardened individually. Revisit with basic auth (htpasswd) or a reverse-proxy auth layer if the registry, or the LAN itself, is ever exposed beyond the house.

## Rate limiting uses in-memory storage, not Redis

`slowapi`'s `Limiter` (`app/rate_limit.py`) uses the default in-memory storage backend rather than the Redis instance the platform already runs. This is correct specifically because the backend intentionally runs as a single uvicorn process — the health/alert/retention pollers are in-process asyncio tasks, and running multiple worker processes would duplicate them. Single process means in-memory rate-limit state needs no cross-process sharing. If that assumption ever changes (multiple backend processes/replicas), the limiter's storage would need to move to Redis at the same time the pollers get split into their own process.

## Loki retention is independent of the app's `LOG_RETENTION_DAYS`

`LOG_RETENTION_DAYS` (backend `.env`) only governs the `audit_logs` and `alert_history` Postgres tables via `poll_retention_forever()`. Loki has its own `retention_period` in `loki/loki-config.yml`, and Prometheus manages its own TSDB retention separately. Each service owns its own storage and retention policy; the app's retention job only ever touches the two tables it created, and a future service adding its own log/data storage is expected to manage its own retention rather than being folded into this job.
