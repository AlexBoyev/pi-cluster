# Wallabag — manual steps

These can't be done via ArgoCD/git by design — secrets never live in this
repo (see `docs/decisions.md`, Wallabag ADR). Do them once, in order, before
or right after the first `kubectl apply`/ArgoCD sync.

## 1. Create the dedicated Postgres role + database

Wallabag gets its own scoped role in the existing platform Postgres, not the
shared `pi_cluster` superuser — if this credential ever leaks, blast radius
is one household service's read-later list, not the whole platform.

```bash
ssh admin@10.100.102.10
DB_PASSWORD=$(openssl rand -base64 24)
echo "Save this password somewhere — you'll need it for step 2: $DB_PASSWORD"
docker exec -i pi-cluster-postgres-1 psql -U pi_cluster -d pi_cluster <<SQL
CREATE ROLE wallabag WITH LOGIN PASSWORD '$DB_PASSWORD';
CREATE DATABASE wallabag OWNER wallabag;
SQL
```

## 2. Create the Kubernetes Secret

Two values: the Postgres password from step 1, and a stable app secret
(`SYMFONY__ENV__SECRET` — must never change once set, or every session
breaks).

```bash
sudo k3s kubectl create namespace wallabag --dry-run=client -o yaml | sudo k3s kubectl apply -f -
sudo k3s kubectl create secret generic wallabag-secret \
  --namespace wallabag \
  --from-literal=database-password='<paste the password from step 1>' \
  --from-literal=symfony-secret="$(openssl rand -base64 32)"
```

(The namespace command is harmless to run even after ArgoCD has already
created it — `apply` is idempotent.)

## 3. Apply / wait for ArgoCD sync

Manifests in this directory sync automatically (`k8s/apps/` is ArgoCD-managed
— unlike `k8s/traefik/`, see `docs/architecture.md` §13). Or apply directly
to skip the ~3 minute wait:

```bash
sudo k3s kubectl apply -f k8s/apps/wallabag/
```

## 4. Create the two real accounts

Once the pod is `Ready` (check `sudo k3s kubectl get pods -n wallabag` —
first boot is slow, see `docs/operations.md`), visit
`http://wallabag.pi-cluster.lan` and register the first account through the
UI while registration is still open from the image's default. Register the
second account the same way, then immediately do step 5.

## 5. Disable registration

Registration is closed by default (`SYMFONY__ENV__FOSUSER_REGISTRATION:
"false"` in `configmap.yaml`) — this step is verifying that's actually in
effect, not turning it off. Visit `http://wallabag.pi-cluster.lan/register`
after creating both accounts; it should refuse new signups. If it doesn't,
something about the ConfigMap didn't apply — check
`sudo k3s kubectl describe configmap wallabag-config -n wallabag` before
assuming the app itself is misbehaving.

## Not done here (accepted tradeoffs — see `docs/decisions.md`)

- Password reset does not work (mailer intentionally unconfigured). Both
  users have SSH access to reset a password by hand if needed:
  `sudo k3s kubectl exec -n wallabag deploy/wallabag -- bin/console fos:user:change-password <username>`.
- Public/Cloudflare Tunnel access is a separate, later change — this is
  LAN-only (`wallabag.pi-cluster.lan`) for now.
