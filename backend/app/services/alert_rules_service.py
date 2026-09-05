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


class AlertRuleError(Exception):
    """User-facing error (duplicate name, not found) - distinct from a
    transport/SSH failure, which raises normally."""


class AlertRulesService:
    async def _read_raw(self) -> str:
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
        await ssh_service.exec_command(_HOST, f"echo {encoded} | base64 -d > {_REMOTE_FILE}")

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
        result = await ssh_service.exec_command(_HOST, git_cmd)
        logger.info("alert-rules git publish: %s", result)

        reload_result = await ssh_service.exec_command(
            _HOST, "curl -sf -X POST http://localhost:9090/-/reload"
        )
        logger.info("prometheus reload: %s", reload_result or "(empty response, likely OK)")

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
