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

---

# ADR: Household Services — Wallabag (first of four)

Wallabag, Vikunja, Paperless-ngx, and Firefly III are planned as self-hosted apps for household use (2 users), unrelated to the pi-cluster platform itself — they don't manage the cluster, they just run on it. Wallabag goes first specifically because it's the smallest, to prove out the patterns the other three inherit cheaply. The decisions below are the actual deliverable; Wallabag is the test case.

## D1 — Storage: `local-path` + `nodeSelector: pi-node3`, not NFS

Verified before deciding, not assumed: the cluster's only `StorageClass` is `local-path` (K3s's built-in provisioner). No NFS server exists anywhere — `nfs-kernel-server` isn't installed on pi-node1, no `/etc/exports`.

Rejected NFS from pi-node1 despite it being the more "obvious" choice for a stateful workload that might move nodes: it isn't infrastructure that already exists, it's a new build (server + exports + a CSI provisioner), and it trades one coupling for a worse one — instead of "pi-node3 down means Wallabag is down" (simple, already how every other per-node thing on this cluster fails), you get "pi-node1's NFS daemon becomes a dependency for every workload's storage, cluster-wide." That's a bigger, newer failure mode in exchange for pod-portability a 2-user read-later app doesn't need. Revisit if a real cross-node-portability need shows up later.

**Consequences, not objections — written down now while still theoretical:**
- `local-path`'s PV carries a hard `nodeAffinity` to whichever node first provisioned it. Draining pi-node3 does **not** reschedule Wallabag elsewhere — the pod goes `Pending` forever, since no other node can satisfy that PVC. See `docs/operations.md` for the drain-impact table this creates (which household service dies when which node is drained).
- Moving a service to a different node later is a **manual** procedure — copy the hostPath directory to the new node, delete and recreate the PV/PVC pointing at the new node — not a live reschedule. Documented once now in `docs/operations.md` rather than reconstructed during an incident.

## D2 — Database: new `wallabag` database inside the existing platform Postgres

Rejected a dedicated Postgres pod (another instance to run and back up separately) and SQLite (corrupts under concurrent access, serializes writes, and — decisively — Wallabag's data directory lives on `local-path`, and SQLite-over-network-filesystem semantics are exactly the failure mode `local-path` doesn't have, but a future NFS migration would reintroduce if a service were still on SQLite). Reusing the platform Postgres means no new pod and it inherits an already-running, already-backed-up instance.

**This does widen the backup role** (`ansible/roles/backup` previously dumped only `pi_cluster`) — done as part of this change, not deferred: `backup_postgres_databases` is now a list (`[pi_cluster, wallabag]`), looped in `backup.sh.j2`. Confirmed covered, per the prompt's own request to state this explicitly.

## D3 — Ingress: nginx wildcard fallback + multi-worker upstream, LAN-only for now

Found while investigating, not assumed: there was no working path from any hostname to Traefik on pi-node2/3/4 at all. `dnsmasq` wildcards `*.pi-cluster.lan`/`*.cluster.download` both resolve to pi-node1; `nginx` there only proxies a fixed set of hardcoded hostnames; Traefik was excluded from pi-node1 in an earlier change (it fought Docker Compose's `nginx` for the same host ports). Any new K8s-Ingress-based hostname would 404 at nginx before ever reaching Traefik. This blocked all four household services, not just Wallabag.

Rejected a per-hostname nginx block (works for Wallabag, then costs an nginx edit + full Jenkins platform deploy for every future service — coupling user workloads to the platform's own delivery pipeline, exactly the boundary kept clean everywhere else). Rejected pointing the dnsmasq wildcard straight at a worker IP instead of through nginx: simpler, but breaks every existing platform hostname (they only exist behind nginx on pi-node1) and gets no failover.

Built instead: one `server` block matching `*.pi-cluster.lan` and `*.cluster.download`, proxying to an `upstream` listing all three workers (`10.100.102.16/17/12:80`) with `max_fails`/`fail_timeout` for passive health checks — one worker down doesn't take routing down with it. (Placement after the specific server blocks is for file readability, not correctness — nginx's `server_name` matching picks an exact match over a wildcard regardless of block order.) Vikunja, Paperless, and Firefly need nothing but a K8s `Ingress` from here — no nginx change, no platform deploy.

**LAN-only for now** (`wallabag.pi-cluster.lan`), Cloudflare Tunnel exposure deferred as a separate later change — agreed explicitly rather than doing both at once. Whatever Cloudflare-side change that needs (adding one more Public Hostname route, or nothing at all if the tunnel already has a wildcard route — unconfirmed, lives in Cloudflare's dashboard, not this repo) is out of scope here.

## D4 — Namespace: `wallabag`, dedicated (one namespace per service)

Each of the four gets its own namespace: its own `ResourceQuota` so one service's spike can't starve the others, a clean uninstall (delete the namespace), no `postgres`/`redis` Service name collisions between services, and RBAC/NetworkPolicy that scopes cleanly per service later. The cost (a few more manifests, a few more API objects) is negligible at this scale. This becomes the convention for Vikunja, Paperless, and Firefly.

## Configuration notes (verified against the live registry and upstream source, not assumed)

- Image `wallabag/wallabag:2.6.14` — confirmed via direct Docker Hub registry API query that this tag's manifest list includes `linux/arm64` (not just amd64).
- `SYMFONY__ENV__DOMAIN_NAME=http://wallabag.pi-cluster.lan` — must match the real URL exactly, including scheme; this is Wallabag's single most common misconfiguration (breaks generated links, the browser extension, and the mobile app in ways that look unrelated).
- `SYMFONY__ENV__FOSUSER_REGISTRATION` defaults to `false` upstream — registration is closed out of the box; set explicitly anyway for clarity. Verify the toggle again after creating the two real accounts (belt-and-suspenders, not because the default is expected to change).
- First-run migration: **corrected after actually deploying it** — reading the entrypoint source (previous entry here) turned out to only be half the picture. The entrypoint has its own bootstrap logic using `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` — a *separate* set of variables from the `SYMFONY__ENV__DATABASE_*` ones the app itself uses, mirroring the standard `postgres` image's own convention, undocumented anywhere this session could find. Without them, `POPULATE_DATABASE` is silently ignored. And because D2 pre-creates the `wallabag` role/database (for the isolation reasons above — see D2), the entrypoint sees "database already exists" and skips install anyway, concluding it's already set up when it isn't. Net result: `wallabag:install` has to be run once manually after first deploy (`k8s/apps/wallabag/README.md` step 4). The alternative — giving the entrypoint the platform Postgres *superuser* credential so it can self-create everything — was considered and rejected: it would mean Wallabag's own Secret holds a credential capable of reading/writing the entire platform database, defeating D2's isolation rationale for a small one-time convenience.
- Mailer: left at the image's default (effectively unconfigured) — **password reset will not work**. Documented as an explicit accepted tradeoff, not silently broken; revisit if it turns out to matter for 2 users who both have direct SSH access to reset a password by hand if needed.
- `SYMFONY__ENV__SECRET` is generated and stored only in the cluster Secret (`kubectl create secret`, manual step, never in git) — stable across restarts by design (it's read from the Secret, not regenerated).
- No AI/enrichment in this phase. `.env.example` gets placeholder `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` entries, clearly marked unused and reserved for a future companion enrichment service — never built into the Wallabag container itself.

## Three infrastructure bugs found by actually deploying Wallabag, not writing about it

Deploying end-to-end (not just applying manifests and declaring done) surfaced three real, previously-undiscovered bugs — none of them Wallabag-specific; all three would have blocked Vikunja/Paperless/Firefly identically, and two of them were silently breaking things cluster-wide already:

**Traefik's ClusterRole never granted `discovery.k8s.io/endpointslices` or `nodes`** (`k8s/traefik/traefik.yaml`) — only the legacy core/v1 `endpoints`. Traefik v3 needs EndpointSlices to resolve backend pod IPs; without that permission, every Ingress-routed request 404'd, for any workload, on every node — visible only as repeated `reflector.go` "forbidden" warnings in Traefik's own logs, nothing surfaced to `kubectl get ingress` (which showed everything as configured correctly). This means **no Ingress-based workload had ever actually worked on this cluster** before this fix — the sample-nginx.yaml example in `k8s/apps/` was never verified end-to-end either. Fixed by adding both permissions and restarting the DaemonSet.

**Promtail's Kubernetes pod-log scraping matched zero targets, cluster-wide, since the file was first written.** Two compounding bugs: the `__path__` glob was one directory level too shallow (`/var/log/pods/*$1/*.log` vs the real `<ns>_<pod>_<uid>/<container>/*.log` structure — confirmed with `find` against the actual filesystem), and — the real blocker — Promtail auto-injects a `spec.nodeName=$hostname` selector to scope each DaemonSet pod to its own node, but a container's hostname (`os.Hostname()`, the kernel/UTS-namespace one — **not** the `HOSTNAME` env var, which does nothing here and was tried first) defaults to the pod's own name, not the node's. The selector became `spec.nodeName=<promtail's own pod name>`, matching nothing. Fixed with `hostNetwork: true` (same reason node-exporter already has it), confirmed node hostnames match K8s node names exactly before relying on it. Verified fixed by reading Promtail's own `/config` endpoint and confirming `namespace`/`pod`/`container` labels and real log lines started arriving in Loki.

**Both were invisible to `kubectl get` health checks** — pods showed `Running`, `Ready`, `0 restarts` throughout; the failures were entirely in what those pods *did*, not whether they started. Diagnosed by checking actual behavior (RBAC via `kubectl auth can-i` and reading logs directly, not assuming; the raw K8s API worked fine when impersonating Promtail's own identity, which is what pointed at Promtail's own client rather than permissions). Worth remembering for the next three services: a green pod status proves nothing about whether ingress or logging actually work for it.
