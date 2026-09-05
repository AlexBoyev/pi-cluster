---
name: deploy
description: Deploy pi-cluster changes to pi-node1 (10.100.102.10) — picks the fast SCP+restart path for backend-only Python changes, or the git push + Jenkins path for everything else, then verifies with a health check.
---

# Deploy pi-cluster

pi-node1 runs the whole platform via Docker Compose. There are two independent
ways to get a change onto it — pick based on what changed, not out of habit.

## 1. Decide the path

- **Backend-only Python change** (nothing under `frontend/`, no
  `docker-compose.yml`/`Dockerfile`/dependency changes) → **Path A**
  (SCP + restart, ~seconds).
- **Anything else** (frontend, docker-compose, new dependencies, Alembic
  migrations, infra files) → **Path B** (git push + Jenkins). Frontend must be
  built inside Docker — there is no npm on the Pi, so Path A cannot serve
  frontend changes.

If it's not obvious from the diff which category the change falls in, ask.

## 2. Path A — backend-only, immediate

```bash
# from F:/Projects/pi-cluster
scp -r backend/app admin@10.100.102.10:/home/admin/pi-cluster/backend/
ssh admin@10.100.102.10 "cd /home/admin/pi-cluster && echo 'admin' | sudo -S docker compose restart backend"
```

**If the change adds or edits a `.env` variable, use `up -d` instead of
`restart`.** Confirmed live, not a guess: `docker compose restart` reuses the
existing container's already-baked-in environment and does **not** re-read
`.env` — a newly added var comes back empty even though the file on disk is
correct. `docker compose up -d backend` recomputes the config (including
`.env`) and recreates the container if it changed:

```bash
ssh admin@10.100.102.10 "cd /home/admin/pi-cluster && echo 'admin' | sudo -S docker compose up -d backend"
```

`restart` is fine — faster, no recreate — for pure code changes that don't
touch `.env`.

Then verify:

```bash
curl -sf http://10.100.102.10:8000/health
```

Don't report the deploy as done without a passing health check — a restarted
container that fails to come up looks identical to a successful one until you
check.

## 3. Path B — everything else, via Jenkins

```bash
git add <files>
git commit -m "..."
git push origin master
```

Jenkins polls GitHub every 2 minutes and, on `master`, runs: rsync workspace →
`/home/admin/pi-cluster` → `docker compose up -d --build backend frontend` →
`alembic upgrade head` → health check. Wait roughly 2-3 minutes after the
push, then verify the same way:

```bash
curl -sf http://10.100.102.10:8000/health
```

If it doesn't come back healthy after a few minutes, check the Jenkins build
at `http://10.100.102.10:8080` before assuming the deploy landed — ArgoCD
(`k8s/apps/`) is a separate pipeline and won't show Docker Compose failures.

## Notes

- Jenkins' rsync runs as root on pi-node1, which leaves synced files
  root-owned — this is why Path A (direct SCP as `admin`) is the faster loop
  for backend-only iteration instead of waiting on Jenkins every time.
- Path A and Path B can drift: after a Path A hotfix, the next `git push`
  still overwrites pi-node1 with whatever's in the repo, so make sure the
  hotfix is committed too or Jenkins will revert it on the next poll.
