# Pi-Cluster Roadmap

## Phase 0 — Foundation ✓
- [x] Repository structure and documentation
- [x] Docker Compose scaffold
- [x] Backend scaffold (FastAPI, SQLAlchemy, Alembic)
- [x] Frontend scaffold (React, TypeScript, Vite)
- [x] Migrations applied and API responding

## Phase 1 — Cluster Inventory ✓
- [x] Node registration API
- [x] Node listing API
- [x] Seed initial cluster nodes (pi-node1–4)
- [x] Dashboard node list

## Phase 2 — Node Health ✓
- [x] SSH connectivity check (paramiko)
- [x] CPU, memory, disk, uptime, temperature via SSH
- [x] Node status tracking (ONLINE / OFFLINE / DEGRADED / UNKNOWN)
- [x] Background health polling (30s interval, asyncio)
- [x] Health API endpoint with Redis cache (90s TTL)
- [x] Dashboard health cards with ring gauges

## Phase 3 — Observability ✓
- [x] Backend `/metrics` endpoint (prometheus-fastapi-instrumentator)
- [x] Custom Prometheus Gauges per node (CPU, RAM, disk, temp, uptime)
- [x] Prometheus scrape config
- [x] Grafana auto-provisioned datasource + dashboard
- [x] Light-blue admin UI with sidebar navigation

## Phase 4 — Authentication ✓
- [x] JWT-based login / token refresh
- [x] Protected API routes (FastAPI dependency)
- [x] Frontend auth flow (login page, token storage)
- [x] Role-based access (admin / viewer)

## Phase 5 — CI/CD Pipeline ✓
- [x] Jenkins deployed as Docker service on pi-node1 (:8080)
- [x] Jenkins pipeline: Checkout → Sync → Deploy → Migrate → Health Check
- [x] SCM polling every 2 minutes (triggers on any master push)
- [ ] Webhook from Git repo to Jenkins (optional, polling sufficient)
- [ ] Automated docker build and push to local registry

## Phase 6 — Kubernetes + GitOps ✓
- [x] K3s server on pi-node1, agents on pi-node2/3/4
- [x] ArgoCD deployed on K3s (:30443)
- [x] ArgoCD Application watching k8s/apps/ in this repo
- [x] Sample nginx workload deployed via GitOps
- [ ] Workload scheduling and placement policies

## Phase 7 — Orchestration ✓
- [x] Workload API (create / list / delete K8s deployments)
- [x] Kubernetes Python client integrating with K3s via kubeconfig
- [x] Capacity-aware placement (picks node with most free CPU)
- [x] Node cordon / uncordon via API and dashboard UI
- [x] Workloads page in frontend (deploy form, live table, capacity cards)

## Phase 8 — Load Balancing ✓
- [x] Traefik DaemonSet deployed on K3s (HostPort 80/443, IngressClass traefik)
- [x] Workload API creates K8s Service + Ingress on container_port
- [x] TLS termination via Traefik built-in self-signed cert
- [x] Ingress host auto-assigned as `<name>.pi-cluster.local`
- [x] Frontend shows ingress URL as clickable link in workloads table

## Phase 9 — Audit Logging ✓
- [x] `audit_logs` table: action, resource_type, resource_name, actor, status, detail, timestamp
- [x] AuditService wraps all writes with best-effort semantics (never breaks the operation)
- [x] Audit events captured for: workload create/delete/scale/image-update/env-update, node cordon/uncordon
- [x] Actor resolved from JWT-authenticated user on every mutation
- [x] GET /api/v1/audit with limit/offset pagination
- [x] Audit Log page in frontend: event table, action/status badges, filter by type, load more

## Phase 10 — Node Exporter ✓
- [x] prometheus/node-exporter DaemonSet on all 4 K3s nodes via ArgoCD (k8s/apps/node-exporter.yaml)
- [x] Prometheus scrape job for node-exporter with per-node node_name labels
- [x] Grafana dashboard rewritten with node_exporter metrics (CPU %, memory %, disk %, temp, network)
- [x] Two new panels: Network Receive and Network Transmit per node
- [x] SSH metric collection retained for health card status; Grafana uses native Prometheus data

## Phase 11 — Alerting ✓
- [x] Prometheus alerting rules: NodeDown (critical), HighCPU/Memory/Disk/Temperature (warning)
- [x] AlertManager service (Docker Compose, port 9093) with grouping and repeat intervals
- [x] Backend `/api/v1/alerts` endpoint proxies Prometheus alert state, sorted by severity
- [x] AlertsPanel on dashboard: all-clear state, firing/pending badges, severity color, duration
- [x] Panel border changes to amber/red when alerts are active

## Phase 12 — Workload Scaling ✓
- [x] `PATCH /workloads/{name}/scale` endpoint with replica range validation (1–10)
- [x] K8s `patch_namespaced_deployment` applies replica count immediately
- [x] DB `update_replicas` keeps workload record in sync
- [x] Audit logged on every scale operation (success + failure)
- [x] Inline − / count / + controls in workloads table; disabled at bounds or while scaling

## Phase 13 — Pod Log Viewer ✓
- [x] `GET /workloads/{name}/logs?tail=N` — reads last N lines from a running pod via K8s API
- [x] Selects a Running pod first, falls back to first available pod
- [x] Auth-protected (any authenticated user); returns workload name, pod name, log text
- [x] LogsModal component: dark terminal viewport, auto-scrolls to bottom, Refresh button, Esc/overlay-click to close
- [x] "Logs" button per row in workloads table; opens modal without leaving the page

## Phase 14 — Rolling Image Updates ✓
- [x] `PATCH /workloads/{name}/image` endpoint with admin auth and audit logging
- [x] K8s `patch_namespaced_deployment` updates container image in-place (rolling restart)
- [x] DB `update_image` keeps workload record in sync
- [x] Inline image editor in workloads table: click image → editable input, Enter to apply, Escape to cancel
- [x] Row dims during update; edit pencil icon appears on hover

## Phase 15 — K8s Events Viewer ✓
- [x] `GET /workloads/{name}/events` — lists K8s events for the deployment and its pods, sorted newest-first, capped at 50
- [x] Matches events by exact deployment name or pod name prefix (`<name>-`)
- [x] `WorkloadEvent` schema: type, reason, message, object_name, count, first_time, last_time
- [x] EventsModal: structured table with Warning/Normal type badges, age formatting, amber row highlight for warnings
- [x] "Events" button per row in workloads table (amber hover)

## Phase 16 — Environment Variables ✓
- [x] Migration 0006: `env_vars JSONB` column on workloads table (default `{}`)
- [x] `WorkloadCreate` accepts `env_vars: dict[str, str]`; K8s deployment created with `V1EnvVar` list
- [x] `PATCH /workloads/{name}/env` — replaces env vars, triggers K8s rolling restart, audited
- [x] `EnvModal`: key/value table editor with add/remove rows, Save & restart pods, Escape/overlay to close
- [x] "Env" button per workload row (green hover); pre-populated with current vars

## Phase 17 — Resource Limits ✓
- [x] Migration 0007: `cpu_limit VARCHAR(16)` and `memory_limit VARCHAR(16)` on workloads table (defaults: 500m / 256Mi)
- [x] `WorkloadCreate` accepts optional `cpu_limit` / `memory_limit`; K8s deployment created with `V1ResourceRequirements`
- [x] `PATCH /workloads/{name}/resources` — updates K8s container resource limits via rolling patch, audited
- [x] `ResourcesModal`: shows static requests (fixed at deploy), editable CPU/memory limit inputs, OOM vs throttling hint
- [x] "Resources" button per workload row (purple hover)
- [x] Deploy form includes optional CPU limit and memory limit fields

## Phase 18 — Workload Restart ✓
- [x] `POST /workloads/{name}/restart` — patches `kubectl.kubernetes.io/restartedAt` annotation to trigger rolling restart (identical to `kubectl rollout restart`)
- [x] Admin-only; audited with actor
- [x] No DB schema change — restart is a live K8s operation only
- [x] "Restart" button per workload row (orange hover); shows spinner while in-flight

## Phase 19 — Health Probes ✓
- [x] Migration 0008: `liveness_path VARCHAR(255)` and `readiness_path VARCHAR(255)` nullable columns on workloads table
- [x] `WorkloadCreate` accepts optional `liveness_path` / `readiness_path`; K8s deployment created with HTTP `V1Probe` objects using container port (initialDelay 15s/5s, period 10s, failureThreshold 3)
- [x] `PATCH /workloads/{name}/probes` — replaces probe config with rolling patch, audited; 400 if container port absent
- [x] `ProbesModal`: two path inputs (liveness + readiness), port hint, warning when no container port, teal Apply button
- [x] "Probes" button per workload row (teal hover)
- [x] Deploy form includes optional liveness/readiness path fields
- [x] Fixed: `WorkloadResponse` constructors in scale/image/env responses were missing `cpu_limit`, `memory_limit` — all constructors now complete

## Phase 20 — Live Auto-Refresh ✓
- [x] Workloads table polls every 15 seconds via `setInterval`; polling pauses automatically when any modal is open
- [x] `useRef` pattern prevents stale-closure issues with the poll callback
- [x] Pulsing green "Live" dot indicator in the section header; switches to grey "Paused" when a modal is open
- [x] "Xs ago / just now" age counter updates every second; resets on each successful fetch
- [x] README updated: workload lifecycle diagram, API reference table, DB schema, migration count

## Phase 21 — Pod Status View ✓
- [x] `GET /workloads/{name}/pods` — lists pods by `app={name}` label selector; returns phase, ready container count, assigned node, pod IP, start time
- [x] `PodInfo` schema: name, phase, node, pod_ip, ready, total, started_at
- [x] `PodsModal`: table with Phase badge (Running/Pending/Failed/Succeeded/Unknown), Ready ratio, Node, IP, Age; Refresh button; Esc/overlay to close
- [x] "Pods" button per workload row (indigo hover); pauses auto-refresh while open

## Phase 22 — Workload Search & Filter ✓
- [x] Name search input (case-insensitive substring match) above the workloads table
- [x] Status filter pills: All / Running / Pending / Failed — active pill adopts the status colour; section header shows "X of Y" when a filter is active

## Phase 23 — Workload Table Sorting ✓
- [x] Clickable column headers for Name, Replicas, Status, Created — click once to sort ascending, again to flip to descending
- [x] Active sort column shows a blue directional arrow; inactive columns show a faded ↕ idle indicator; default sort is Created descending (newest first)

## Phase 24 — Node Drain ✓
- [x] `POST /workloads/nodes/{name}/drain` — cordons the node then evicts all non-DaemonSet, non-static pods via the K8s Eviction API; returns eviction count; admin-only and audit-logged
- [x] Drain button (red hover) on each capacity card beside Cordon/Uncordon; disabled while another drain/cordon is in-flight or node is NotReady

## Phase 25 — Audit Log Filtering ✓
- [x] `GET /api/v1/audit` gains optional `status` and `resource_type` query params; filtering is server-side against the full log
- [x] `AuditRepository.get_recent()` applies SQLAlchemy `where` clauses on status and resource_type when provided
- [x] Audit page filter bar replaced: Status pills (All / Success / Failure) and Type pills (All / Workload / Node)
- [x] Filter change resets pagination and re-fetches from offset 0; Load More carries current filter values
- [x] Action badge palette extended to cover scale, image-update, env-update, restart, probes-update, resources-update, drain

## Phase 26 — Live Pod Metrics ✓
- [x] `GET /workloads/{name}/metrics` — queries Prometheus for actual container CPU (5m rate) and memory (working set) usage
- [x] `WorkloadMetrics` schema: cpu_cores, cpu_limit_cores, memory_bytes, memory_limit_bytes, pod_count, available flag
- [x] Parser functions for K8s resource notation (500m → 0.5 cores, 256Mi → bytes) in service layer
- [x] `MetricsModal`: CPU and memory usage bars (blue/amber/red by % of limit), formatted values, Refresh button
- [x] "Metrics" button per workload row (cyan hover); pauses auto-refresh while open
- [x] Graceful degradation: `available=false` shown as a clear message when Prometheus is unreachable or no data collected

## Phase 27 — Infrastructure as Code ✓
- [x] Ansible inventory targeting real node IPs (10.100.102.10/16/17/12)
- [x] `ansible/playbooks/bootstrap.yml` — packages, cgroups, swap off, UFW on all nodes
- [x] `ansible/playbooks/k3s.yml` — K3s server on pi-node1, agents on pi-node2/3/4; kubeconfig fetched and patched
- [x] `ansible/playbooks/argocd.yml` — ArgoCD install via kubectl, NodePort 30443, apply k8s/apps/
- [x] `ansible/playbooks/platform.yml` — Docker install, repo clone, .env templating, compose up + migrate
- [x] Ansible roles: common, k3s_server, k3s_agent, platform (with Jinja2 env template)
- [x] Helm chart `helm/pi-cluster/` — backend, frontend, PostgreSQL StatefulSet, Redis, Ingress, Secrets
- [x] Terraform `main.tf` — pi-cluster + monitoring namespaces, ClusterRole + ClusterRoleBinding for K8s API access
- [x] Terraform `argocd.tf` — ArgoCD Helm release (argo-helm chart) + ArgoCD Application manifest via kubernetes_manifest
- [x] Terraform providers: hashicorp/kubernetes ~2.27, hashicorp/helm ~2.13; local backend
- [x] `terraform.tfvars.example` for safe variable reference; `.gitignore` excludes tfstate, tfvars, .terraform/
- [x] Secrets never stored in repo — prompted at runtime (Ansible) or passed via --set / tfvars (Helm/Terraform)

## Phase 28 — Deployment Rollback ✓
- [x] `GET /workloads/{name}/history` — lists K8s ReplicaSet-based revision history: revision number, image, creation time, is_current flag
- [x] `POST /workloads/{name}/rollback` — restores the full pod template from the selected ReplicaSet revision; updates DB image field; admin-only and audit-logged (`workload.rollback`)
- [x] `DeploymentRevision` and `WorkloadHistory` schemas; `RollbackRequest` with revision ge=1
- [x] K8sService: `get_rollout_history()` reads deployment revision annotation and RS metadata; `rollback_deployment()` patches deployment spec.template from target RS and returns rolled-back image
- [x] `RollbackModal`: revision list (number, image, age); current revision marked and non-selectable; confirm button disabled until a non-current revision is selected; auto-refresh of workloads table after success
- [x] "History" button per workload row (indigo hover); pauses auto-refresh while modal open
- [x] Audit log: `workload.rollback` action with `revision=N image=…` detail; indigo badge on Audit page

## Phase 29 — Node Detail Page ✓
- [x] `GET /nodes/{node_id}/metrics/history?period=1h|6h|24h` — queries Prometheus range API for 6 metrics per node: CPU%, memory%, disk%, temperature, network Rx/Tx; step auto-selected per period (60s/300s/900s)
- [x] `NodeMetricsService.get_metrics_history()` — sequential async httpx requests per metric, graceful degradation per query (empty list on failure); node_name resolved from DB via node_id
- [x] `MetricPoint` (t, v) and `NodeMetricsHistory` schemas; route validated: period must be 1h/6h/24h
- [x] Prometheus queries use `node_name` label matching prometheus.yml relabeling; temperature via `max(node_thermal_zone_temp{node_name=...})`; network aggregated with `irate` and `sum` across all non-loopback devices
- [x] `NodesPage` — new sidebar page ("Nodes") between Dashboard and Workloads
- [x] Node list view: grid of cards showing name, IP, role badge (CTRL/WORKER), status badge, current CPU load/memory%/disk%/temperature snapshot; "Details →" button per card
- [x] Node detail view: back navigation, header with name/IP/status/role, snapshot row (CPU load, memory with used/total, disk, temp, uptime); 1h/6h/24h period pills
- [x] 6 SVG area sparkline charts in 2-column grid: CPU% (blue), Memory% (green), Disk% (amber), Temperature (red), Network Rx (purple), Network Tx (teal)
- [x] Each chart: subtle grid lines at 25%/50%/75%, area fill, polyline, last-value dot, current/min/max labels; no chart library dependency
- [x] Sidebar version string bumped to Phase 29

## Phase 30 — Alert History ✓
- [x] Migration 0009: `alert_history` table — alert_name, severity, node_name, instance, summary, labels (JSON text), fired_at, resolved_at (nullable)
- [x] `AlertHistoryRepository`: `get_open()`, `create_firing()`, `resolve_firing()`, `get_recent()` with severity and state filters
- [x] Background poller (`poll_alert_history_forever`, 30s interval) — fetches current firing alerts from Prometheus, inserts new episodes, stamps `resolved_at` on cleared alerts; runs alongside the health poller in lifespan
- [x] `GET /api/v1/alert-history/` — paginated (limit/offset), filterable by `severity` and `state` (active/resolved)
- [x] `AlertHistoryEntry` Pydantic schema with `from_attributes = True`
- [x] Alert History page: summary cards (total shown / active / resolved / critical), severity pills (All / Critical / Warning / Info), state pills (All / Active / Resolved)
- [x] Timeline table: Alert, Severity badge, Node, Summary, Fired (relative age), Duration, State badge
- [x] Active rows highlighted in faint red; resolved rows show "Resolved" green badge; active rows show "Active" red badge
- [x] "Alert History" sidebar link (⊛ icon) added between Audit Log and Services
- [x] Sidebar version string bumped to Phase 30

## Phase 31 — Cluster Resource Capacity ✓
- [x] `GET /api/v1/cluster/capacity` — queries K8s for per-node allocatable + pod requests, queries Prometheus for actual CPU/memory used per node; returns cluster totals and per-node breakdown
- [x] `ClusterCapacity` and `NodeCapacityDetail` schemas; CPU in cores (float), memory in bytes (int); Prometheus gracefully skipped if unreachable
- [x] `ClusterService.get_cluster_capacity()` — 2 Prometheus instant queries (mem used, CPU fraction) matched by `node_name` label across all nodes in one request each
- [x] Capacity page: summary cards (total CPU cores, CPU used %, total memory, memory used %), cluster-wide stacked bars (used · requested · free), per-node breakdown cards
- [x] Stacked bar: blue=used, grey=requested-above-used, transparent=free; color shifts to amber at 65%, red at 85%
- [x] Per-node cards: CPU and memory rows with mini bars, used/allocatable/requested labels, Ready/Cordoned badges
- [x] "Capacity" sidebar link (▦ icon); auto-refresh every 30s

## Phase 32 — Cluster-wide K8s Events Feed ✓
- [x] `K8sService.get_cluster_events()` — `list_event_for_all_namespaces()` or scoped to namespace; filtered by type, sorted newest-first, capped at 200
- [x] `GET /api/v1/events/` — params: `namespace`, `event_type`, `limit`; returns `ClusterEvent` list
- [x] `ClusterEvent` schema: namespace, type, reason, message, object_kind, object_name, count, first_time, last_time
- [x] Events page: summary cards (total, warnings, normal, namespace count), namespace dropdown filter, Warning/Normal type pills, live/paused toggle (15s auto-refresh)
- [x] Table: Age, Type badge (Warning amber / Normal blue), Reason, Namespace+Object, Message, Count; Warning rows tinted amber
- [x] "Events" sidebar link (⊜ icon)

## Phase 33 — Namespace Management ✓
- [x] `K8sService`: `list_namespaces()`, `create_namespace(name)`, `delete_namespace(name)`
- [x] `GET /api/v1/namespaces/` — list all K8s namespaces with status, created_at, labels (kubernetes.io/* filtered out)
- [x] `POST /api/v1/namespaces/` — create namespace (admin); protected set: default, kube-system, kube-public, kube-node-lease, monitoring, argocd
- [x] `DELETE /api/v1/namespaces/{name}` — delete namespace (admin); same protection
- [x] `NamespaceInfo` and `NamespaceCreate` (pattern-validated) schemas
- [x] Namespaces page: summary cards, create form with validation, sortable table with Active/Terminating badges, system tag, inline delete confirmation
- [x] WorkloadsPage: namespace filter pills (All ns + unique namespaces from loaded workloads); shown only when 2+ distinct namespaces exist
- [x] "Namespaces" sidebar link (⊟ icon); version bumped to Phase 33

## Phase 34 — User Management ✓
- [x] `UserRepository`: added `get_all()`, `get_by_id()`, `update_role()`, `update_password()`, `delete()`
- [x] `UserResponse`, `UserCreate`, `PasswordChange`, `RoleUpdate` Pydantic schemas
- [x] `GET /api/v1/users/` — list all users (admin-only)
- [x] `POST /api/v1/users/` — create user with username, password (min 8 chars), role (admin/viewer); 409 if username taken
- [x] `PATCH /api/v1/users/{id}/role` — change role (admin-only; cannot change own role)
- [x] `PATCH /api/v1/users/{id}/password` — change password (user for self, admin for anyone)
- [x] `DELETE /api/v1/users/{id}` — delete user (admin-only; cannot delete self)
- [x] Users page: summary cards (total/admins/viewers), create form, user table with inline role dropdown, change-password in-row edit, delete with confirmation; current user highlighted with "you" badge
- [x] "Users" sidebar link (◉ icon) under new "Admin" section

## Phase 35 — Horizontal Pod Autoscaler ✓
- [x] `K8sService`: `get_hpa()`, `apply_hpa()`, `delete_hpa()` using K8s AutoscalingV2 API
- [x] `HPAInfo` schema: min_replicas, max_replicas, cpu_target_pct, current_replicas, current_cpu_pct
- [x] `HPACreate` schema: min_replicas (1–10), max_replicas (1–20), cpu_target_pct (10–100)
- [x] `GET /workloads/{name}/hpa` — returns current HPA or null (authenticated)
- [x] `PUT /workloads/{name}/hpa` — create or replace HPA (admin-only)
- [x] `DELETE /workloads/{name}/hpa` — remove HPA (admin-only)
- [x] `HpaModal`: on open fetches current HPA, shows status bar (current replicas, CPU utilization, target, range); 3-field form (min, max, CPU target); Enable/Update/Remove HPA buttons; CPU over-target shown in amber
- [x] "HPA" action button per workload row (green hover); pauses auto-refresh while open

## Phase 36 — ConfigMap Management ✓
- [x] `K8sService`: `list_configmaps()`, `get_configmap()`, `create_configmap()`, `update_configmap()`, `delete_configmap()`
- [x] `ConfigMapSummary` and `ConfigMapDetail` schemas; `ConfigMapCreate` (name pattern-validated), `ConfigMapUpdate`
- [x] `GET /api/v1/configmaps/` — list ConfigMaps in namespace (authenticated)
- [x] `GET /api/v1/configmaps/{name}` — get full ConfigMap data (authenticated)
- [x] `POST /api/v1/configmaps/` — create ConfigMap with key=value data (admin-only); 409 if already exists
- [x] `PUT /api/v1/configmaps/{name}` — replace ConfigMap data (admin-only)
- [x] `DELETE /api/v1/configmaps/{name}` — delete ConfigMap (admin-only)
- [x] ConfigMaps page: namespace selector (populates from live namespace list), summary cards, create form with textarea (KEY=value lines), key-tag pills per row, edit modal with textarea editor, delete confirmation
- [x] "ConfigMaps" sidebar link (⊞ icon); version bumped to Phase 36

## Phase 37 — Secret Management ✓
- [x] `K8sService`: `list_secrets()` (filters service-account tokens and Helm secrets), `get_secret()` (base64-decodes values to UTF-8), `create_secret()`, `update_secret()`, `delete_secret()`
- [x] `SecretSummary` and `SecretDetail` schemas; `SecretCreate` (name-validated, type field), `SecretUpdate`
- [x] All secret endpoints admin-only (read included); values never logged
- [x] `GET /api/v1/secrets/` — list secrets in namespace (keys only, no values)
- [x] `GET /api/v1/secrets/{name}` — get secret with decoded values
- [x] `POST /api/v1/secrets/` — create with key=value data, type (Opaque/tls/dockerconfigjson)
- [x] `PUT /api/v1/secrets/{name}` — replace data
- [x] `DELETE /api/v1/secrets/{name}` — delete
- [x] Secrets page: namespace selector, create form with type dropdown, key-tag pills per row, View/Edit modal showing per-key "Reveal"/"Hide" toggle (values masked by default), textarea editor for updates, delete confirmation
- [x] "Secrets" sidebar link (⊕ icon); namespace selector populates from live list

## Phase 38 — Services & Ingress Visibility ✓
- [x] `K8sService`: `list_services()` (all namespaces or scoped), `list_ingresses()` using NetworkingV1Api
- [x] `ServicePort`, `ServiceInfo`, `IngressPath`, `IngressRule`, `IngressInfo` schemas
- [x] `GET /api/v1/services` — cluster-wide or namespace-scoped service list
- [x] `GET /api/v1/ingresses` — cluster-wide or namespace-scoped ingress list
- [x] Services & Ingresses page: tab switcher (Services / Ingresses), namespace filter dropdown, summary cards (service count by type, ingress count, unique hosts)
- [x] Services table: Name, Namespace, Type badge (LoadBalancer green / NodePort amber / ClusterIP blue), ClusterIP, Ports with protocol, Selector labels, Created
- [x] Ingresses table: Name, Namespace, IngressClass, Rules (host + path → backend), TLS badge, Created
- [x] "Services" sidebar link (⇌ icon)

## Phase 39 — CronJob Management ✓
- [x] `K8sService`: `list_cronjobs()`, `create_cronjob()` (builds V1CronJob with container, command, env), `set_cronjob_suspend()`, `delete_cronjob()`, `list_cronjob_jobs()` (recent job runs matched by owner reference)
- [x] `CronJobInfo`, `CronJobCreate`, `JobRun` schemas
- [x] `GET /api/v1/cronjobs/` — list all or namespace-scoped CronJobs
- [x] `POST /api/v1/cronjobs/` — create (admin); schedule as cron expression, image, optional command array, env vars
- [x] `PATCH /api/v1/cronjobs/{name}/suspend` — suspend (admin)
- [x] `PATCH /api/v1/cronjobs/{name}/resume` — resume (admin)
- [x] `GET /api/v1/cronjobs/{name}/jobs` — recent job run history
- [x] `DELETE /api/v1/cronjobs/{name}` — delete (admin)
- [x] CronJobs page: namespace filter, summary cards (total/active/suspended), create form (name, namespace, cron schedule, image, command, env vars), table with schedule code badge, Active/Suspended badge, last-run time, Runs modal (job history: status badge, started, duration), Suspend/Resume toggle, delete confirmation
- [x] "CronJobs" sidebar link (⊙ icon); version bumped to Phase 39

## Phases 40-50 — undocumented until now

This roadmap file stopped being updated after Phase 39, even though development kept going in git history through at least Phase 52 plus a batch of unnumbered follow-up work. `README.md` was partially kept in sync (a "Phases 23-52+" pass at one point) but this file wasn't — this is exactly the kind of drift that caused the phase-numbering collision below (this file's own Phase 40-43 entries, added in the same session that wrote this backfill, originally reused numbers 40-43 that had already shipped as different features and were simply never recorded here). Renumbered to 54+ to stop colliding.

Entries below are reconstructed from commit history (messages + diffs), not independently re-verified against current code line-by-line the way earlier phases in this file were when they were written — treat as reasonably accurate, not gospel, until spot-checked.

### Phase 40 — PVC/Storage Management ✓
- `K8sService.list_pvcs()`, `delete_pvc()`, `list_pvs()`; `GET/DELETE /storage/pvcs`, `GET /storage/pvs`
- `StoragePage.tsx`: PVC/PV tabs with status badges, delete confirmation

### Phase 41 — Alert Notifications (Webhook) ✓
- Migration 0010: `notification_channels` table; `NotificationService` dispatches async HTTP webhooks
- Wired into `alert_history_service.py` — fires on new alert firings
- `NotificationsPage.tsx`: manage channels, test button

### Phase 42 — Pod Terminal (WebSocket Exec) ✓
- `WS /ws/exec/{name}` bridges a K8s exec stream via thread + `asyncio.Queue`, `?token=` auth
- `TerminalModal.tsx`: dark terminal UI, ANSI stripping, Ctrl+C/L

### Phase 43 — StatefulSets/DaemonSets, Helm, RBAC Explorer, PVC creation ✓
- Objects page: StatefulSets/DaemonSets with replica/availability badges
- Helm Releases: parses Helm 3 secrets (chart/version/status/revision)
- RBAC Explorer: ClusterRoles (expandable rules), ClusterRoleBindings, Service Accounts by namespace
- Storage: Create PVC form (storage class, access mode, size)

### Phase 44 — Live log streaming ✓
- `WS /ws/logs/{name}` replaces HTTP polling; LIVE badge, filter, auto-scroll, reconnect, 3000-line cap

### Phase 45 — Pod detail view ✓
- `GET /pods/{namespace}/{name}`: containers, resource requests/limits, conditions, recent events
- `PodDetailModal`, opened from `PodsModal`

### Phase 46 — Batch Jobs, Quotas, Alert Rules browser ✓
- Jobs viewer (state, duration, parent CronJob link); ResourceQuotas/LimitRanges with usage bars
- Prometheus Alert Rules browser (grouped by rule group, PromQL expression, active instances)

### Phase 47 — Dedicated Live Logs page ✓
- Full-page log viewer: Namespace → Pod → Container cascade, tail size selector, WebSocket streaming

### Phase 48 — Node SSH terminal + power management ✓
- `WS /ws/ssh/{node_ip}` proxies paramiko `invoke_shell`; `NodeSSHModal`
- `POST /nodes/{id}/restart|shutdown` and cluster-wide `/nodes/all/restart|shutdown` (admin-only, SSH sudo)
- Backend test suite established (`backend/tests/`, later expanded to 307+ tests); Jenkinsfile gained a Test stage

### Phase 49 — Networking & public access ✓
- nginx reverse proxy for friendly local hostnames (`*.pi-cluster.lan`)
- dnsmasq container for network-wide local DNS (host networking, forwards unknown queries upstream)
- Cloudflare Tunnel (`cloudflared`) added for public access via `*.cluster.download`; `.env` removed from git
- Mobile-responsive dashboard layout

### Phase 50 — Access lockdown + Key Vault ✓
- All cluster-management routes made admin-only; viewers get a portal/limited view (verify current exact scope against `backend/app/auth/dependencies.py` before relying on this — reconstructed from an old commit message, not independently re-checked)
- Key Vault page: surfaces Jenkins/ArgoCD/Prometheus/Grafana credentials read from K8s Secrets and the vault API; hidden on the public Cloudflare domain, restricted to LAN via nginx `allow`/`deny` on `/api/v1/vault` (see `nginx/nginx.conf`)
- Jenkins admin password reset from `JENKINS_ADMIN_PASSWORD` on startup; Jenkins excluded from the Compose `up` that Jenkins itself triggers (self-kill prevention)

## Phase 51 — Backup & Disaster Recovery ✓ (applied and verified live)
- [x] `ansible/roles/backup` — nightly script backs up the `pi_cluster` Postgres DB (via `docker exec` on the container directly, so it never needs read access to the root-owned `/home/admin/pi-cluster` Jenkins path) and the K3s control-plane datastore (SQLite online `.backup`, since this is a single-server K3s install using embedded SQLite/kine, not etcd — see the comment in `roles/backup/templates/backup.sh.j2`)
- [x] Backups shipped via rsync over a dedicated SSH key to pi-node4 (`ansible/playbooks/backup.yml` generates the key on pi-node1 and trusts it on pi-node4 — idempotent, safe to re-run)
- [x] Local backups on pi-node1 trimmed to the last 3; remote backups on pi-node4 trimmed to the last 14 (independent retention from the app's `LOG_RETENTION_DAYS` — this is infra backup file retention, a different concern)
- [x] **Applied to the live cluster.** Ran into and fixed three real gaps the first run surfaced: `admin` had no private key for outbound SSH (needed for the self-connection back to pi-node1 and for reaching pi-node4) — generated one and self-authorized it; `admin` has no passwordless sudo — supplied the become password via `ANSIBLE_BECOME_PASS` env var, not written to any file; `backup_target_host: pi-node4` doesn't resolve on pi-node1 (that alias only exists in Ansible's own inventory, and the script runs standalone via cron, not through Ansible) — changed the default to the real IP. pi-node4 authorization for this run was done directly via the same documented `admin`/`SSH_PASSWORD` credential the backend already uses cluster-wide (confirmed working via `sshpass`), since this session didn't have pre-existing SSH access to pi-node4 to run the Ansible play's second play itself.
- [x] **Restore runbook exercised for real**, not just written: restored `postgres.sql.gz` into a scratch database (`restore_drill_test`, same Postgres instance, never touching production) and compared row counts against the live `pi_cluster` database — `users`, `workloads`, `audit_logs`, and `nodes` all matched exactly. Scratch database dropped after verification. K3s datastore restore (stop k3s, replace `state.db`, restart) was not drilled — lower urgency and higher blast radius to rehearse than the Postgres path.

## Phase 52 — Container Registry ✓
- [x] `registry:2` added to `docker-compose.yml` (port 5000, `registry-data` volume) — picked up automatically by Jenkins' existing `docker compose up -d $SERVICES` Deploy stage, no separate rollout needed
- [x] Jenkinsfile `Push to Registry` stage (after Health Check, so it never blocks or races the actual deploy) tags `backend`/`frontend` images with the short git SHA and `latest`, pushes both to `localhost:5000`
- [x] Closes the roadmap's original Phase 5 gap ("Automated docker build and push to local registry") for the platform's own images
- [ ] No auth on the registry (LAN-only, matches Prometheus's existing posture) — revisit if the registry is ever exposed beyond the LAN

## Phase 53 — Log Aggregation (Loki + Promtail) ✓
- [x] `loki` added to `docker-compose.yml` on pi-node1 (port 3100, filesystem storage, own `loki/loki-config.yml` with a 30d `retention_period` — independent of `LOG_RETENTION_DAYS`)
- [x] `promtail` DaemonSet in `k8s/apps/promtail.yaml` (ArgoCD-applied automatically, same as node-exporter/traefik) — self-contained ServiceAccount/ClusterRole/ClusterRoleBinding following the `traefik.yaml` pattern
- [x] Scrapes K3s pod logs across all 4 nodes (`/var/log/pods`, CRI pipeline stage) and Docker Compose container logs on pi-node1 only (`/var/lib/docker/containers`, JSON pipeline stage); pushes to `http://10.100.102.10:3100/loki/api/v1/push`
- [x] Grafana datasource `grafana/provisioning/datasources/loki.yaml` (auto-provisioned on the next Grafana container restart via Jenkins deploy)
- [x] Verified live: `kubectl get pods -n monitoring` shows `promtail` 4/4 Running, 0 restarts, on all 4 nodes. Log content itself (Grafana Explore) not yet spot-checked.

## Phase 54 — Log & Audit Retention ✓
- [x] `LOG_RETENTION_DAYS` env var (default 90) — new `.env` value, `Settings.log_retention_days`
- [x] `poll_retention_forever()` background task (registered in `main.py` lifespan alongside the health/alert pollers) deletes `audit_logs` rows and **resolved** `alert_history` rows older than the cutoff once a day; active/unresolved alerts are never deleted regardless of age
- [x] Scoped strictly to these two Postgres tables — does not touch Loki's or Prometheus's own storage/retention, which are configured independently (see Phase 53)
- [x] Migration `0011_add_retention_indexes` — indexes on `audit_logs.created_at` and `alert_history.resolved_at` so the daily cleanup delete is cheap
- [x] Repository-level tests (`backend/tests/test_retention.py`) verify old rows are deleted, recent rows survive, and active alerts are never touched regardless of age

## Phase 55 — API Rate Limiting ✓
- [x] `slowapi`, in-memory storage (not Redis — deliberate, see `docs/decisions.md`; the app runs single-process because the background pollers are in-process asyncio tasks)
- [x] 300 requests/minute per IP globally via `SlowAPIMiddleware`; 10/minute specifically on `POST /auth/login` for brute-force protection
- [x] Disabled during tests (`conftest.py` — the session-scoped test client would otherwise trip it across every login-heavy test); `test_rate_limit.py` re-enables it in isolation to prove it actually returns 429
- [x] Dropped `--reload` from the backend's production `docker-compose.yml` command — a dev flag with no reason to run in production

## Phase 56 — Pod-Level Alerting (kube-state-metrics) + Traefik/pi-node1 Fix ✓
- [x] Root-caused via live investigation: a Traefik pod on pi-node1 had burned 100+ min of CPU over 10+ hours (cgroup-confirmed to be the live container, not an orphan) because it fights Docker Compose's `nginx` for host ports 80/443 — Traefik's DaemonSet tolerated the control-plane taint specifically to also run there
- [x] Fixed with a `nodeAffinity` excluding pi-node1 (`k8s/traefik/traefik.yaml`) — Traefik now runs pi-node2/3/4 only; pi-node1's own routing was always nginx's job
- [x] `kube-state-metrics` added (`k8s/apps/kube-state-metrics.yaml`, Deployment + NodePort 30108 — ClusterIP wouldn't be reachable from Prometheus, which runs in Docker Compose outside the K8s pod network) — this class of incident (pod-level crash-loop) was invisible to every prior alert rule, all node-level
- [x] Two new Prometheus alert rules: `PodCrashLooping`, `PodNotReady`
- [x] nginx now LAN-restricts `prometheus.*`/`alertmanager.*` (`allow 10.100.102.0/24; deny all` — same pattern as `/api/v1/vault`) since neither has its own auth and both are reachable through the Cloudflare Tunnel; verified against the live nginx binary before rollout
- [x] Jenkinsfile reloads Prometheus after deploy (`curl -X POST .../-/reload`) — `prometheus.yml`/`alerts.yml` are volume-mounted, so `docker compose up -d` alone doesn't pick up changes to them
- [ ] Cluster-wide restart pattern (all 4 Traefik pods restarted ~simultaneously, ~10h before the investigation) not fully root-caused — the pi-node1-specific port conflict is fixed, but the broader trigger is still unknown

## Phase 57 — Documentation Consistency Pass ✓
- [x] Fixed CLAUDE.md: removed a stale duplicate "Current Priority" section that contradicted the top of the file (an artifact of an earlier partial edit); expanded the Stack list, which omitted K3s/Jenkins/ArgoCD/Traefik/Loki/registry/Ansible/Terraform/Helm/dnsmasq/Cloudflare Tunnel entirely
- [x] Fixed architecture.md/decisions.md/README.md: etcd → embedded SQLite/kine (3 places), `/opt/pi-cluster` → `/home/admin/pi-cluster` (the real Jenkins path, in architecture.md, decisions.md, and this file's own `/deploy` skill), `alex`+key-only → `admin`+key-and-password (matches actual verified SSH behavior)
- [x] Backfilled Phases 40-50 (see above) — real, shipped work that stopped being recorded in this file after Phase 39, discovered via `git log` when the frontend's own `Phase 50` sidebar string didn't match this file's `Phase 39` end point
- [ ] Frontend sidebar phase string was manually bumped to match the true latest number as of this pass — it will go stale again the next time a phase ships without updating `App.tsx`; there's no automated check for this drift
