# Operations

Runbooks for things that come up during normal operation. Platform-level
operations (Jenkins/ArgoCD deploy, K3s, backups) are in `docs/architecture.md`
and `docs/decisions.md`; this file is about running the cluster day to day —
starting with household services, since that's what first needed it.

## Node drain impact

The dashboard's Node Drain feature (cordons + evicts) affects different
things depending on which node, because household services are pinned to
specific workers (`docs/decisions.md`, D1) and pi-node1 runs the platform
outside Kubernetes entirely.

| Node | What actually happens when drained |
|---|---|
| pi-node1 | Docker Compose stack (backend, Postgres, Grafana, Jenkins, etc.) is **unaffected** — it's not managed by K3s, draining only evicts K8s DaemonSet pods there (node-exporter, promtail), which just get recreated once uncordoned. Not that draining pi-node1 is generally advisable anyway; it's the control plane. |
| pi-node2 | Reserved for Paperless (not yet deployed). Currently just loses one of its three Traefik replicas — the other two on pi-node3/4 keep serving ingress traffic (`nginx`'s `upstream` has passive health checks for exactly this). No household-service impact yet. |
| pi-node3 | **Wallabag goes down.** Its pod can't reschedule elsewhere — the PVC's `nodeAffinity` ties it to pi-node3 (`local-path`, not portable). The pod sits `Pending` until pi-node3 is uncordoned. |
| pi-node4 | Backup target, not a K8s workload host for anything yet. K8s-level drain doesn't stop the nightly backup cron (that's a plain SSH/rsync job on pi-node1, not scheduled *on* pi-node4) — but if pi-node4 is offline outright (not just drained), that night's backup fails to ship; local copies on pi-node1 still exist until the next cleanup cycle trims them. |

## Manually migrating a household service to a different node

`local-path` PVCs aren't portable — there's no live reschedule. This is the
procedure, written once while it's still theoretical (per the ADR) rather
than reconstructed during an incident.

1. Scale the Deployment to 0 so nothing is writing: `kubectl scale deploy/<name> -n <namespace> --replicas=0`
2. Find where the PV's data actually lives: `kubectl get pv $(kubectl get pvc <name> -n <namespace> -o jsonpath='{.spec.volumeName}') -o jsonpath='{.spec.hostPath.path}'` — a path under `/opt/local-path-provisioner` on the **old** node.
3. Copy that directory to the same path on the **new** node (`rsync` over SSH between the two Pi nodes directly).
4. Delete the old PVC and PV (`kubectl delete pvc/pv ...`) — data already copied, safe once step 3 is confirmed.
5. Edit the service's `nodeSelector` (in its `deployment.yaml`) to the new node, and re-create the PVC — `local-path`'s `WaitForFirstConsumer` binding mode means it provisions fresh at the new node the moment the pod schedules there, picking up the copied directory if the path matches, or starting empty if it doesn't (verify the copied directory is at the exact path the new PV expects before scaling back up).
6. Scale back to 1, confirm the pod is healthy and the data is actually there before considering it done.

This is manual and a little fiddly by design — `local-path` was chosen specifically because household services don't need automatic portability (`docs/decisions.md`, D1). If this procedure starts getting used often, that's a signal to revisit the NFS alternative considered-and-rejected there.

## Wallabag

### Deploy

See `k8s/apps/wallabag/README.md` for the full manual-steps sequence (Postgres role, Secret, first accounts). Manifests sync via ArgoCD automatically once the Secret exists (`k8s/apps/` is watched — unlike `k8s/traefik/`, see `docs/architecture.md` §13).

### First boot is slow — this is expected

The image's entrypoint runs `composer install` on every container start (confirmed by reading the entrypoint source, not assumed) — slow on Pi-class ARM/SD storage. The `startupProbe` is tuned generously (up to 5 minutes) for exactly this; don't assume a crash if the pod isn't `Ready` within the first minute or two. Every pod restart pays this cost again, not just the first one — expect restarts to take a while, not just the initial deploy.

### Upgrade

1. Check the release notes at the [wallabag GitHub releases page](https://github.com/wallabag/wallabag/releases) for the target version specifically for database migration notes — Symfony/Doctrine migrations run automatically on start (same entrypoint behavior as first-install), but a major version bump can carry breaking config changes that migrations don't cover.
2. Back up first — trigger `/home/admin/backup.sh` manually on pi-node1 rather than waiting for the nightly cron, so there's a fresh restore point immediately before the upgrade.
3. Edit the pinned tag in `k8s/apps/wallabag/deployment.yaml`, commit, push. ArgoCD applies it (or `kubectl apply -f k8s/apps/wallabag/` to skip the wait).
4. Watch the pod come up (`kubectl get pods -n wallabag -w`) and check Loki (Grafana Explore, filter `namespace="wallabag"`) for migration errors during startup.
5. **Rollback**: revert the tag in git (or `kubectl set image`), then restore the `wallabag` database from the pre-upgrade backup if the new version already wrote data in a format the old version can't read — check the migration notes from step 1 to know whether that's actually necessary before doing it.

### Add a user later

Registration is disabled after the first two accounts (`docs/decisions.md`). Don't re-enable it even briefly to add a third — use the CLI instead, which never opens a public signup window:

```bash
sudo k3s kubectl exec -n wallabag deploy/wallabag -- bin/console fos:user:create <username> <email> <password>
```
