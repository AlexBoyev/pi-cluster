import json
from concurrent.futures import ThreadPoolExecutor

import paramiko

from app.config import settings

# Runs on the Pi via python3 stdin; returns a JSON object with raw metrics.
_METRICS_SCRIPT = b"""
import json, subprocess
mem = {}
with open('/proc/meminfo') as f:
    for line in f:
        parts = line.split()
        if len(parts) >= 2:
            mem[parts[0].rstrip(':')] = int(parts[1]) * 1024
try:
    df = subprocess.check_output(['df', '-B1', '/'], stderr=subprocess.DEVNULL)
    row = df.decode().split('\\n')[1].split()
    disk_total, disk_used = int(row[1]), int(row[2])
except Exception:
    disk_total = disk_used = 0
uptime = float(open('/proc/uptime').read().split()[0])
try:
    temp = int(open('/sys/class/thermal/thermal_zone0/temp').read().strip()) / 1000.0
except Exception:
    temp = None
load = float(open('/proc/loadavg').read().split()[0])
print(json.dumps({
    'memory_total':    mem.get('MemTotal', 0),
    'memory_available': mem.get('MemAvailable', 0),
    'disk_total':      disk_total,
    'disk_used':       disk_used,
    'uptime_seconds':  uptime,
    'temperature_celsius': temp,
    'load_1m':         load,
}))
"""

_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="ssh")


class SSHService:
    def _run_sync(self, host: str) -> dict:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            host,
            username=settings.ssh_username,
            password=settings.ssh_password,
            timeout=settings.ssh_connect_timeout,
        )
        try:
            stdin, stdout, _ = client.exec_command("python3 -")
            stdin.write(_METRICS_SCRIPT)
            stdin.close()
            stdout.channel.settimeout(settings.ssh_command_timeout)
            return json.loads(stdout.read().decode())
        finally:
            client.close()

    async def collect_metrics(self, host: str) -> dict:
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(_pool, self._run_sync, host)

    def _exec_sync(self, host: str, command: str) -> str:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            host,
            username=settings.ssh_username,
            password=settings.ssh_password,
            timeout=settings.ssh_connect_timeout,
        )
        try:
            if command.startswith("sudo "):
                # Feed the SSH password to sudo via stdin so it works without
                # a TTY and without requiring NOPASSWD in sudoers.
                stdin, stdout, stderr = client.exec_command("sudo -S " + command[5:])
                stdin.write(settings.ssh_password + "\n")
                stdin.flush()
                stdin.channel.shutdown_write()
            else:
                _, stdout, stderr = client.exec_command(command)
            stdout.channel.settimeout(settings.ssh_command_timeout)
            try:
                out = stdout.read().decode(errors="replace")
                err = stderr.read().decode(errors="replace")
            except Exception:
                # Channel closed mid-read because the node is rebooting — that's fine.
                out, err = "", ""
            # sudo -S writes the password prompt to stderr; strip it.
            err = "\n".join(
                l for l in err.splitlines()
                if "[sudo]" not in l and "password for" not in l.lower()
            )
            return (out + err).strip()
        finally:
            client.close()

    async def exec_command(self, host: str, command: str) -> str:
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(_pool, self._exec_sync, host, command)


ssh_service = SSHService()
