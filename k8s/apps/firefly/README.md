# Firefly III — manual steps

These can't be done via ArgoCD/git by design — secrets never live in this
repo (see `docs/decisions.md`). Do them once, in order, before or right
after the first `kubectl apply`/ArgoCD sync.

## 1. Create the dedicated Postgres role + database

```bash
ssh admin@10.100.102.10
DB_PASSWORD=$(openssl rand -base64 24)
echo "Save this password somewhere — you'll need it for step 2: $DB_PASSWORD"
docker exec -i pi-cluster-postgres-1 psql -U pi_cluster -d pi_cluster <<SQL
CREATE ROLE firefly WITH LOGIN PASSWORD '$DB_PASSWORD';
CREATE DATABASE firefly OWNER firefly;
SQL
```

## 2. Create the Kubernetes Secret

Five values: the Postgres password from step 1, a 32-character `APP_KEY`
(Firefly's encryption key — must never change once set, or existing data
becomes unreadable), a 32-character `STATIC_CRON_TOKEN` (see D4 in
`docs/decisions.md` for why it exists), and the Brevo SMTP login + API key.

```bash
kubectl create namespace firefly --dry-run=client -o yaml | kubectl apply -f -
kubectl create secret generic firefly-secret \
  --namespace firefly \
  --from-literal=db-password='<paste the password from step 1>' \
  --from-literal=app-key="$(head /dev/urandom | LC_ALL=C tr -dc 'A-Za-z0-9' | head -c 32)" \
  --from-literal=cron-token="$(head /dev/urandom | LC_ALL=C tr -dc 'A-Za-z0-9' | head -c 32)" \
  --from-literal=mail-username='<Brevo SMTP login, e.g. xxxxxx@smtp-brevo.com>' \
  --from-literal=mail-password='<Brevo SMTP API key>'
```

(The namespace command is harmless to run even after ArgoCD has already
created it — `apply` is idempotent.)

## 3. Apply / wait for ArgoCD sync

Manifests in this directory sync automatically (`k8s/apps/` is ArgoCD-managed,
Traefik included as of 2026-09-07). Or apply directly to skip the ~3 minute
wait:

```bash
kubectl apply -f k8s/apps/firefly/
```

## 4. First admin account

Firefly has no CLI user-create command the way Wallabag/Vikunja do — the
first account is created through the setup wizard on first visit
(`https://firefly.cluster.download`, from inside the LAN or via the tunnel
once the Cloudflare route exists — see step 6). Because `AUTHENTICATION_GUARD=
remote_user_guard` is already active (`docs/decisions.md` Firefly D2), the
account's identifier needs to match whatever pi-cluster reports as the
verified user — **confirm live whether that's username or email** before
creating it; this was flagged in the ADR as unverified, not assumed to work
either way.

## 5. nginx dedicated block

Firefly needs its own `server` block (not the shared household-services
wildcard) — same reasoning and same shape as Paperless's. Add to
`nginx/nginx.conf`, mirroring the existing `paperless.*` block exactly but
with `server_name firefly.pi-cluster.lan firefly.cluster.download;`. Not
included as an automatic step here since it's a platform file, not a
`k8s/apps/` manifest — deploys via Jenkins on the next push, not ArgoCD.

## 6. Cloudflare Tunnel routes

Two Public Hostname routes to add manually (same manual step every prior
service needed): `firefly.cluster.download` → `http://10.100.102.10:80`,
and `firefly-import.cluster.download` → `http://10.100.102.10:80`.

## 7. Data Importer setup

Visit `https://firefly-import.cluster.download` (gated by the standard
`pi_sso` wildcard — needs an active platform login first, same as any other
household-service tile). Its setup wizard asks for a Firefly III Personal
Access Token: generate one from Firefly's own UI (Options → Profile →
OAuth → Personal Access Tokens) and paste it in — nothing to configure in
this repo, no token stored in `.env` or a Secret.

## 8. First import — CSV, not bank API

See `docs/decisions.md` Firefly D1 for why: bank-API auto-sync
(GoCardless/Nordigen, SaltEdge) is EU/UK PSD2-specific and there's no
regulatory basis to expect Israeli bank coverage. Export a CSV from the
bank's own online banking and run it through the Data Importer's manual
mapping wizard instead — works with any bank, no cooperation needed. Save
the resulting column-mapping profile in the wizard once verified correct,
so future months are a re-upload, not a re-mapping.

## Not done here (accepted tradeoffs, or genuinely unverified — see `docs/decisions.md`)

- Bank-API auto-sync not attempted — CSV is the real path for this
  household, per D1.
- `AUTHENTICATION_GUARD_HEADER=HTTP_REMOTE_USER` and whether the guard
  matches by username or email — both need confirming against the real
  running instance, not assumed correct from documentation alone.
- No confirmed unauthenticated lightweight HTTP endpoint for probes as of
  writing — `deployment.yaml` uses TCP-only probes; upgrade to HTTP once a
  real endpoint is verified.
- Data on the PVC (CSV upload staging) is not covered by the backup role
  (Postgres-only) — same gap every prior service's PVC already has.
