# Vikunja — manual steps

These can't be done via ArgoCD/git by design — secrets never live in this
repo (see `docs/decisions.md`). Do them once, in order, before or right
after the first `kubectl apply`/ArgoCD sync.

## 1. Create the dedicated Postgres role + database

```bash
ssh admin@10.100.102.10
DB_PASSWORD=$(openssl rand -base64 24)
echo "Save this password somewhere — you'll need it for step 2: $DB_PASSWORD"
docker exec -i pi-cluster-postgres-1 psql -U pi_cluster -d pi_cluster <<SQL
CREATE ROLE vikunja WITH LOGIN PASSWORD '$DB_PASSWORD';
CREATE DATABASE vikunja OWNER vikunja;
SQL
```

## 2. Create the Kubernetes Secret

Four values: the Postgres password from step 1, a stable JWT secret (must
never change once set, or every session/refresh-token is invalidated), and
the Brevo SMTP login + API key (see "SMTP relay" below).

```bash
kubectl create namespace vikunja --dry-run=client -o yaml | kubectl apply -f -
kubectl create secret generic vikunja-secret \
  --namespace vikunja \
  --from-literal=database-password='<paste the password from step 1>' \
  --from-literal=jwt-secret="$(openssl rand -base64 32)" \
  --from-literal=mailer-username='<Brevo SMTP login, e.g. xxxxxx@smtp-brevo.com>' \
  --from-literal=mailer-password='<Brevo SMTP API key>'
```

(The namespace command is harmless to run even after ArgoCD has already
created it — `apply` is idempotent.)

## 3. SMTP relay (Brevo)

Shared with the separate security-alert system — one Brevo account/API key
covers both, distinct sender addresses for readability (`vikunja@` here,
`alerts@` for the alert system). See `docs/decisions.md` D2 for the full
reasoning and the deliverability fix (SPF/DKIM/DMARC records) required
before mail actually lands in an inbox — `250 OK, queued` from Brevo does
**not** mean delivered.

## 4. Apply / wait for ArgoCD sync

Manifests in this directory sync automatically (`k8s/apps/` is ArgoCD-managed).
Or apply directly to skip the ~3 minute wait:

```bash
kubectl apply -f k8s/apps/vikunja/
```

## 5. Create the two real accounts + the shared team

Registration is closed (`VIKUNJA_SERVICE_ENABLEREGISTRATION=false`). Create
both accounts via the CLI:

```bash
kubectl exec -n vikunja deploy/vikunja -- ./vikunja user create -u <username> -e <email> -p '<password>'
```

Run it twice, once per user. Then, in the web UI (either account):

1. Settings → Teams → create a team, e.g. "Household" — add the other
   account to it.
2. For every project you want shared, Project Settings → Share → share
   with the "Household" team (Read & Write) instead of the individual
   user — this is the pattern to keep using, including when a third user
   (e.g. a child, later) joins: add them to the team once, they inherit
   every project already shared with it.

## 6. CalDAV app password (per user, per device)

Vikunja's CalDAV endpoint (`/dav/principals/<username>/`) authenticates
with a dedicated **app password**, not the account password — this also
limits the blast radius of CalDAV's inherent Basic-Auth-bypasses-2FA
exposure. Each user creates their own in Settings → CalDAV. See
`docs/operations.md` for the iOS/DAVx5 client setup steps.

## 7. Verify registration is actually closed

From a device **outside** the LAN (mobile data, not home WiFi):

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://vikunja.cluster.download/register
```

Should not offer account creation — same check already done for Wallabag.

## Auto-login bridge (shipped)

`VIKUNJA_BRIDGE_CREDENTIALS` in the platform's own `.env` (not this
directory — consumed by the FastAPI backend, not the Vikunja pod) is a
JSON map of `{"<pi-cluster username>": "<that person's Vikunja password>"}`.
A pi-cluster user with no entry just falls through to Vikunja's own login
screen — nothing breaks, they just don't get the one-click convenience.

**Adding a user to the bridge later**: add their entry to the JSON object
in `.env`, then `docker compose up -d backend` on pi-node1 — **not**
`restart`, which reuses the container's already-loaded environment and
silently ignores the `.env` change (confirmed live during this deploy).

CLI-created accounts land with `status = 1` (`StatusEmailConfirmationRequired`)
in Vikunja 2.6.0 and cannot log in — including through the bridge — until
confirmed. Either have the person click the confirmation email (needs
working SMTP, see D2), or set it directly:

```sql
UPDATE users SET status = 0 WHERE username = '<username>';
```

## Not done here (accepted tradeoffs — see `docs/decisions.md`)

- Attachments on the PVC are not covered by the backup role (Postgres-only)
  — same gap Wallabag's own attachments already have.
