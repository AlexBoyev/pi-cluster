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

# Runs on the Pi via python3 stdin. Loads all cores with `timeout N bash -c
# 'while :; do :; done'` per core - deliberately not stress-ng: no package
# install, no internet dependency, and it's the exact method already used
# live to diagnose the 2026-09-08 pi-node3/pi-node2 undervoltage incident
# (see docs/decisions.md). Samples vcgencmd every INTERVAL seconds for the
# full duration so a live undervoltage/throttle event is actually caught,
# not just a before/after snapshot.
_STRESS_SCRIPT_TEMPLATE = """
import json, subprocess, time, os

DURATION = {duration}
INTERVAL = {interval}

def _run(args):
    try:
        return subprocess.check_output(args, stderr=subprocess.DEVNULL, timeout=5).decode().strip()
    except Exception:
        return None

def read_vcgencmd():
    thr = _run(['vcgencmd', 'get_throttled'])
    temp = _run(['vcgencmd', 'measure_temp'])
    volt = _run(['vcgencmd', 'measure_volts'])
    try:
        val = int(thr.split('=')[1], 16) if thr else 0
    except Exception:
        val = 0
    try:
        t = float(temp.split('=')[1].rstrip("'C")) if temp else None
    except Exception:
        t = None
    try:
        v = float(volt.split('=')[1].rstrip('V')) if volt else None
    except Exception:
        v = None
    return {{
        'throttled_hex': hex(val),
        'undervoltage_now': bool(val & 0x1),
        'freq_capped_now': bool(val & 0x2),
        'throttled_now': bool(val & 0x4),
        'undervoltage_occurred': bool(val & 0x10000),
        'throttled_occurred': bool(val & 0x40000),
        'temp_celsius': t,
        'volts': v,
    }}

ncores = os.cpu_count() or 4
start = time.time()
baseline = read_vcgencmd()
baseline['elapsed_seconds'] = 0.0

workers = [
    subprocess.Popen(['timeout', str(DURATION), 'bash', '-c', 'while :; do :; done'])
    for _ in range(ncores)
]

samples = []
while time.time() - start < DURATION:
    time.sleep(INTERVAL)
    r = read_vcgencmd()
    r['elapsed_seconds'] = round(time.time() - start, 1)
    samples.append(r)

for w in workers:
    w.wait()

final = read_vcgencmd()
final['elapsed_seconds'] = round(time.time() - start, 1)

print(json.dumps({{'baseline': baseline, 'samples': samples, 'final': final, 'ncores': ncores}}))
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

    def _run_stress_sync(self, host: str, duration: int, interval: int) -> dict:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            host,
            username=settings.ssh_username,
            password=settings.ssh_password,
            timeout=settings.ssh_connect_timeout,
        )
        try:
            script = _STRESS_SCRIPT_TEMPLATE.format(duration=duration, interval=interval)
            stdin, stdout, _ = client.exec_command("python3 -")
            stdin.write(script.encode())
            stdin.close()
            # The remote script itself blocks for `duration` seconds - give
            # the channel read real headroom on top of that, not the default
            # short command timeout meant for instant commands.
            stdout.channel.settimeout(duration + settings.ssh_connect_timeout + 15)
            return json.loads(stdout.read().decode())
        finally:
            client.close()

    async def run_stress_test(self, host: str, duration: int, interval: int = 5) -> dict:
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(
            _pool, self._run_stress_sync, host, duration, interval
        )

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
