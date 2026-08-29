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
