import logging
import time

import httpx

from app.config import settings
from app.schemas.node_metrics import MetricPoint, NodeMetricsHistory

logger = logging.getLogger(__name__)

_PERIODS: dict[str, tuple[int, int]] = {
    "1h":  (3_600,  60),
    "6h":  (21_600, 300),
    "24h": (86_400, 900),
}


def _parse_range(data: dict) -> list[MetricPoint]:
    result = data.get("data", {}).get("result", [])
    if not result:
        return []
    pts = []
    for ts, val in result[0].get("values", []):
        try:
            pts.append(MetricPoint(t=float(ts), v=float(val)))
        except (ValueError, TypeError):
            continue
    return pts


async def get_metrics_history(node_name: str, period: str) -> NodeMetricsHistory:
    seconds, step = _PERIODS.get(period, _PERIODS["1h"])
    now = time.time()
    n = node_name

    queries = {
        "cpu_pct": (
            f'100 - (avg(rate(node_cpu_seconds_total{{mode="idle",node_name="{n}"}}[2m])) * 100)'
        ),
        "memory_pct": (
            f'100 - (node_memory_MemAvailable_bytes{{node_name="{n}"}}'
            f' / node_memory_MemTotal_bytes{{node_name="{n}"}} * 100)'
        ),
        "disk_pct": (
            f'(1 - node_filesystem_free_bytes{{node_name="{n}",mountpoint="/"}}'
            f' / node_filesystem_size_bytes{{node_name="{n}",mountpoint="/"}}) * 100'
        ),
        "temperature_c": f'max(node_thermal_zone_temp{{node_name="{n}"}})',
        "net_rx_bps": (
            f'sum(irate(node_network_receive_bytes_total{{node_name="{n}",device!="lo"}}[2m]))'
        ),
        "net_tx_bps": (
            f'sum(irate(node_network_transmit_bytes_total{{node_name="{n}",device!="lo"}}[2m]))'
        ),
    }

    params_base = {"start": now - seconds, "end": now, "step": step}
    results: dict[str, list[MetricPoint]] = {k: [] for k in queries}

    async with httpx.AsyncClient(timeout=10.0) as client:
        for key, query in queries.items():
            try:
                resp = await client.get(
                    f"{settings.prometheus_url}/api/v1/query_range",
                    params={"query": query, **params_base},
                )
                resp.raise_for_status()
                results[key] = _parse_range(resp.json())
            except Exception as exc:
                logger.warning("Prometheus range query failed [%s] for %s: %s", key, node_name, exc)

    return NodeMetricsHistory(node_name=node_name, period=period, **results)
