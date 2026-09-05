# Paperless-ngx — manual steps

These can't be done via ArgoCD/git by design — secrets never live in this
repo (see `docs/decisions.md`). Do them once, in order, before or right
after the first `kubectl apply`/ArgoCD sync.

## 1. Create the dedicated Postgres role + database

```bash
ssh admin@10.100.102.10
DB_PASSWORD=$(openssl rand -base64 24)
echo "Save this password somewhere — you'll need it for step 2: $DB_PASSWORD"
docker exec -i pi-cluster-postgres-1 psql -U pi_cluster -d pi_cluster <<SQL
CREATE ROLE paperless WITH LOGIN PASSWORD '$DB_PASSWORD';
CREATE DATABASE paperless OWNER paperless;
SQL
```

**Do this before the nightly backup cron runs** — `ansible/roles/backup`
already includes `paperless` in its database list, and the backup script
runs with `set -euo pipefail`: a `pg_dump` against a database that doesn't
exist yet aborts the whole run, including the K3s datastore snapshot.

## 2. Create the Kubernetes Secret

Five values: the Postgres password from step 1, a Django `SECRET_KEY`
(stable — regenerating it invalidates every existing session), the initial
admin account, and a Samba password for the consume-folder share.

```bash
kubectl create namespace paperless --dry-run=client -o yaml | kubectl apply -f -
kubectl create secret generic paperless-secret \
  --namespace paperless \
  --from-literal=database-password='<paste the password from step 1>' \
  --from-literal=secret-key="$(openssl rand -base64 48)" \
  --from-literal=admin-user='admin' \
  --from-literal=admin-password="$(openssl rand -base64 18)" \
  --from-literal=samba-password="$(openssl rand -base64 18)"
```

`PAPERLESS_ADMIN_USER`/`PAPERLESS_ADMIN_PASSWORD` create the superuser
automatically on first boot — the officially recommended approach for
platforms (like Kubernetes) where running `createsuperuser` interactively
isn't practical. It never overwrites an existing account, safe to leave set
permanently.

## 3. Apply / wait for ArgoCD sync

Manifests in this directory sync automatically (`k8s/apps/` is
ArgoCD-managed). Or apply directly to skip the ~3 minute wait:

```bash
kubectl apply -f k8s/apps/paperless/
```

## 4. Add the Cloudflare Tunnel route

Same manual step as Wallabag/Vikunja — add a Public Hostname route in the
Cloudflare Zero Trust dashboard: `paperless.cluster.download` →
`http://10.100.102.10:80`. Lives entirely in Cloudflare's dashboard, not
this repo.

## 5. Verify Hebrew OCR — the single most important check in this phase

A bad Hebrew OCR result does not error — it silently writes garbage into
the search index, which poisons search permanently and invisibly. Do this
before considering the phase done, not after:

1. Scan or photograph a real Hebrew-and-English document.
2. Drop it into the Samba share (step 6) or upload it via the web UI.
3. Once processed, open the document and **read the extracted text with
   your own eyes** — compare it against the original. Don't just check that
   *some* text was extracted.
4. Search for a distinctive word or phrase from the document in Hebrew —
   confirm it returns *that* document.
5. Confirm the date was parsed correctly if the document has a DD/MM/YYYY
   date on it (Settings → the document's own detected date field).

If the extracted text is garbled: check `kubectl -n paperless logs
deploy/paperless | grep -i ocr` for the actual Tesseract invocation and
confirm `heb` really installed (`PAPERLESS_OCR_LANGUAGES=heb` triggers an
apt install at container startup — the log shows whether it succeeded).

## 6. Samba share (primary ingestion path)

Connect using the `paperless` account and the `samba-password` from step 2:

- **Windows**: File Explorer → address bar → `\\10.100.102.16\inbox`
- **macOS**: Finder → Go → Connect to Server → `smb://10.100.102.16/inbox`
- **iOS**: Files app → Browse → ⋯ → Connect to Server →
  `smb://10.100.102.16/inbox`
- **Android**: most file managers support "Add network location" with the
  same address

`10.100.102.16` is pi-node2's real IP — this share runs with
`hostNetwork: true` specifically so it binds the standard SMB port 445
directly (a K8s NodePort's 30000+ range isn't SMB-client-friendly). LAN
only, by construction — this share is never reachable through the
Cloudflare Tunnel (`cloudflared` only ever forwards to `nginx:80`) and has
no mDNS/discovery advertisement (the `smbd-only` image variant), so it
won't show up by browsing — always connect to the address directly.

Anything dropped into the share lands in Paperless's consume folder within
seconds (filesystem inotify, not polling) and disappears once processed —
that's expected, the original is stored in the `media/` volume after
consumption.

## 7. Add a user later

No self-registration to disable (unlike Wallabag/Vikunja) — Paperless never
had one. Create additional accounts from the admin UI (⚙ → Users & Groups)
or:

```bash
kubectl exec -n paperless deploy/paperless -- python3 manage.py createsuperuser
```

## Capacity

The media volume has no alert of its own — `local-path`'s PVC size is
advisory, not an enforced quota (K3s's provisioner doesn't apply a real
filesystem quota per PVC), so the number that actually matters is
pi-node2's real disk usage, which the existing `HighDisk` Prometheus rule
already alerts on at 80% for *any* node. A dedicated "Paperless volume"
alert would just watch the identical underlying number under a different
name — not added, deliberately, rather than duplicated.

## Reindexing the search index

```bash
kubectl exec -n paperless deploy/paperless -- python3 manage.py document_index reindex
```

No invented timing estimate here — see `docs/decisions.md` D3. Time this
for real against your actual document count and record the number in
`docs/operations.md`.

## Bulk import (the first import will be hundreds of documents)

OCR on a Pi 4 is slow, and the whole point of pi-node2 being dedicated to
Paperless was to avoid starving anything else — but a few hundred documents
consumed all at once will still peg the container's own CPU limit for a
while. Options, in order of simplicity:

1. **Throttle via the consume folder**: drop documents into the Samba share
   in smaller batches (e.g. 20-30 at a time) rather than all at once, and
   let each batch finish before adding more.
2. **Off-hours**: do the bulk drop late at night — nothing else on
   pi-node2 competes for the CPU regardless of time, but this avoids any
   perceived slowness if someone else is actively using Paperless at the
   same time.
3. **Pre-OCR elsewhere** (last resort, not needed unless 1-2 prove too
   slow): OCR documents on a faster machine first, feeding Paperless
   already-searchable PDFs (`PAPERLESS_OCR_MODE=skip` means it won't
   redo work that's already there).

## Not done here (accepted tradeoffs — see `docs/decisions.md`)

- Attachments/media on the PVC are not covered by the backup role (Postgres
  only) — same gap Wallabag's/Vikunja's own attachments already have.
- Barcode/ASN splitting — not enabled, designed to stay possible later if
  bulk scanning is ever used, per the brief.
- Email/IMAP ingestion — designed for (native to Paperless, configured via
  its own UI, no extra container needed) but left disabled.
- AI enrichment (summarization, extracted amounts/expiry dates) — explicitly
  out of scope, a future companion service polling Paperless's REST API
  using its own token auth (kept reachable specifically so this stays
  possible — see `docs/decisions.md` D4), never built into this container.
