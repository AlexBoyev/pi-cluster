import base64
import io
import logging
import shlex

from ruamel.yaml import YAML

from app.config import settings
from app.services.ssh_service import ssh_service

logger = logging.getLogger(__name__)

_REMOTE_REPO = "/home/admin/pi-cluster"
_REMOTE_FILE = f"{_REMOTE_REPO}/prometheus/alerts.yml"
_HOST = settings.k8s_api_host

# Round-trip loader: preserves comments, key order, and formatting on parts
# of the file this doesn't touch - a plain yaml.safe_load()/dump() round
# trip would silently strip every comment in this file on the first UI
# edit (confirmed by inspecting prometheus/alerts.yml's real content
# before choosing this over the stdlib yaml module already used
# elsewhere in this codebase).
_yaml = YAML()
_yaml.preserve_quotes = True
_yaml.indent(mapping=2, sequence=4, offset=2)
# Default width wraps long expr/description values across multiple lines -
# confirmed live: every existing rule's long PromQL expression and
# description got reflowed on the very first edit, even though only one
# unrelated rule actually changed, which is noisy diff churn for no
# reason. A wide width keeps long scalars on one line, matching how this
# file was originally hand-written.
_yaml.width = 4096


class AlertRuleError(Exception):
    """Validation error - duplicate name on create, not-found on
    update/delete. Maps to 409/404; the request never touched SSH."""


class AlertRulePublishError(Exception):
    """A publish step (chown, git sync, write, commit/push, or Prometheus
    reload) actually failed - maps to 502, distinct from AlertRuleError so
    the API layer doesn't call an infrastructure failure a "conflict" or
    "not found". Always carries a real, checked reason: this class exists
    because the original code logged SSH command output and returned
    success regardless of it, silently swallowing both a write that failed
    with Permission Denied and a push rejected as non-fast-forward."""


class AlertRulesService:
    async def _run_checked(self, command: str, step: str) -> str:
        """ssh_service.exec_command returns text, never raises on a
        nonzero exit - append a sentinel and check for it explicitly, so a
        failed step is a real error instead of silent success."""
        marker = "__PI_CLUSTER_OK__"
        output = await ssh_service.exec_command(_HOST, f"{command} && echo {marker}")
        if marker not in output:
            raise AlertRulePublishError(f"{step} failed: {output.strip() or '(no output)'}")
        return output

    async def _sync_repo(self) -> None:
        """Called before every read AND before every write - the edit has
        to be computed from truly current state, not whatever this local
        clone happened to have sitting around.

        Jenkins' rsync runs as root, leaving files in this repo root-owned
        - confirmed live as the actual cause of a "successful" write that
        silently never landed (admin got Permission Denied, never
        surfaced). ssh_service already special-cases any command starting
        with "sudo " to feed the SSH password via stdin (sudo -S).

        The local clone at this path is kept current by Jenkins' rsync,
        never by git - its own HEAD can silently drift arbitrarily far
        behind origin/master (confirmed live: found it frozen since this
        repo's Phase 4/5, months of history behind). Synced every call,
        not just once, or a later push builds on a stale base and gets
        rejected as non-fast-forward - which the old code also failed to
        detect in the first place."""
        await self._run_checked(f"sudo chown -R admin:admin {_REMOTE_REPO}", "Fixing file ownership")
        await self._run_checked(
            f"cd {_REMOTE_REPO} && git fetch origin && git reset --hard origin/master",
            "Syncing local repo to origin/master",
        )

    async def _read_raw(self) -> str:
        await self._sync_repo()
        return await ssh_service.exec_command(_HOST, f"cat {_REMOTE_FILE}")

    def _parse(self, raw: str):
        return _yaml.load(raw)

    def _dump(self, data) -> str:
        buf = io.StringIO()
        _yaml.dump(data, buf)
        return buf.getvalue()

    async def _write_and_publish(self, content: str, commit_message: str) -> None:
        # Base64, not a quoted heredoc - a raw YAML/PromQL payload going
        # through shell quoting is exactly what corrupted a bcrypt hash
        # earlier this session; base64's alphabet has no shell-special
        # characters at all, so there's nothing left to escape.
        encoded = base64.b64encode(content.encode()).decode()
        await self._run_checked(
            f"echo {encoded} | base64 -d > {_REMOTE_FILE}", "Writing alerts.yml"
        )

        # admin@pi-node1 has no git push credentials of its own (confirmed
        # live: git push --dry-run fails with no cached auth, and
        # user.name/user.email were never even set). The token is passed
        # as an explicit one-off push target, never written into
        # .git/config, so it never appears in `git remote -v`.
        git_cmd = (
            f"cd {_REMOTE_REPO} && "
            f"git config user.name 'pi-cluster-admin-panel' && "
            f"git config user.email 'admin-panel@cluster.download' && "
            f"git add prometheus/alerts.yml && "
            f"git commit -m {shlex.quote(commit_message)} && "
            f"git push https://x-access-token:{settings.github_pat}"
            f"@github.com/AlexBoyev/pi-cluster.git master"
        )
        result = await self._run_checked(git_cmd, "Publishing to git")
        logger.info("alert-rules git publish: %s", result)

        # NOT curl .../-/reload - prometheus.yml/alerts.yml are bind-mounted
        # as individual FILES (docker-compose.yml), not a directory. A
        # single-file Docker bind mount binds to the specific inode it
        # resolved at container-start; git checkout replaces files via a
        # new inode (not an in-place edit), so a long-running container
        # keeps serving that orphaned old inode forever regardless of how
        # many times reload is called. Confirmed live: a fresh write plus a
        # successful reload call still left the container reading
        # 21-hour-stale content until it was recreated. Same root cause
        # documented in the Jenkinsfile's own Deploy stage, which had the
        # identical bug via rsync instead of git.
        await self._run_checked(
            f"cd {_REMOTE_REPO} && docker compose up -d --force-recreate prometheus",
            "Recreating Prometheus to pick up the new rule",
        )

    async def create_rule(
        self, group: str, alert: str, expr: str, for_: str,
        severity: str, summary: str, description: str,
    ) -> None:
        data = self._parse(await self._read_raw())
        groups = data.setdefault("groups", [])
        target = next((g for g in groups if g["name"] == group), None)
        if target is None:
            target = {"name": group, "interval": "30s", "rules": []}
            groups.append(target)
        if any(r.get("alert") == alert for r in target["rules"]):
            raise AlertRuleError(f"Rule '{alert}' already exists in group '{group}'")
        target["rules"].append({
            "alert": alert,
            "expr": expr,
            "for": for_,
            "labels": {"severity": severity},
            "annotations": {"summary": summary, "description": description},
        })
        await self._write_and_publish(
            self._dump(data), f"feat: add alert rule {alert} (via admin panel)"
        )

    async def update_rule(
        self, group: str, alert: str, expr: str, for_: str,
        severity: str, summary: str, description: str,
    ) -> None:
        data = self._parse(await self._read_raw())
        for g in data.get("groups", []):
            if g["name"] != group:
                continue
            for r in g.get("rules", []):
                if r.get("alert") == alert:
                    r["expr"] = expr
                    r["for"] = for_
                    r["labels"] = {"severity": severity}
                    r["annotations"] = {"summary": summary, "description": description}
                    await self._write_and_publish(
                        self._dump(data), f"fix: update alert rule {alert} (via admin panel)"
                    )
                    return
        raise AlertRuleError(f"Rule '{alert}' not found in group '{group}'")

    async def delete_rule(self, group: str, alert: str) -> None:
        data = self._parse(await self._read_raw())
        for g in data.get("groups", []):
            if g["name"] != group:
                continue
            before = len(g.get("rules", []))
            g["rules"] = [r for r in g.get("rules", []) if r.get("alert") != alert]
            if len(g["rules"]) != before:
                await self._write_and_publish(
                    self._dump(data), f"chore: remove alert rule {alert} (via admin panel)"
                )
                return
        raise AlertRuleError(f"Rule '{alert}' not found in group '{group}'")


alert_rules_service = AlertRulesService()
