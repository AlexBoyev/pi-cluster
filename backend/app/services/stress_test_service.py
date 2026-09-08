import asyncio
import logging
from datetime import datetime, timezone

from app.schemas.node import NodeResponse
from app.schemas.stress_test import NodeStressResult, StressTestReport, ThrottleReading
from app.services.ssh_service import ssh_service

logger = logging.getLogger(__name__)


def _reading(raw: dict | None) -> ThrottleReading | None:
    return ThrottleReading.model_validate(raw) if raw else None


def _build_node_result(node: NodeResponse, raw: dict | Exception) -> NodeStressResult:
    if isinstance(raw, Exception):
        logger.warning("Stress test lost contact with %s: %s", node.name, raw)
        return NodeStressResult(
            node_name=node.name,
            ip_address=node.ip_address,
            reachable=False,
            error=str(raw),
            verdict="crashed_or_unreachable",
        )

    baseline = _reading(raw.get("baseline"))
    samples = [ThrottleReading.model_validate(s) for s in raw.get("samples", [])]
    final = _reading(raw.get("final"))
    all_readings = [r for r in [baseline, *samples, final] if r is not None]

    temps = [r.temp_celsius for r in all_readings if r.temp_celsius is not None]
    volts = [r.volts for r in all_readings if r.volts is not None]
    undervoltage_detected = any(r.undervoltage_now for r in all_readings)
    throttled_detected = any(r.throttled_now for r in all_readings)

    if undervoltage_detected:
        verdict = "undervoltage_under_load"
    elif throttled_detected:
        verdict = "throttled_under_load"
    else:
        verdict = "clean"

    return NodeStressResult(
        node_name=node.name,
        ip_address=node.ip_address,
        reachable=True,
        ncores=raw.get("ncores"),
        baseline=baseline,
        samples=samples,
        final=final,
        max_temp_celsius=max(temps) if temps else None,
        min_volts=min(volts) if volts else None,
        undervoltage_detected=undervoltage_detected,
        throttled_detected=throttled_detected,
        verdict=verdict,
    )


def _summarize(nodes: list[NodeStressResult]) -> str:
    crashed = [n.node_name for n in nodes if n.verdict == "crashed_or_unreachable"]
    undervolted = [n.node_name for n in nodes if n.verdict == "undervoltage_under_load"]
    throttled = [n.node_name for n in nodes if n.verdict == "throttled_under_load"]

    if not crashed and not undervolted and not throttled:
        return "All nodes held steady under load - no undervoltage or throttling detected."

    parts = []
    if crashed:
        parts.append(f"lost contact with {', '.join(crashed)} (likely crashed/rebooted under load)")
    if undervolted:
        parts.append(f"live undervoltage on {', '.join(undervolted)}")
    if throttled:
        parts.append(f"CPU throttling on {', '.join(throttled)}")
    return "Power issue detected: " + "; ".join(parts) + "."


class StressTestService:
    async def run(self, nodes: list[NodeResponse], duration_seconds: int) -> StressTestReport:
        started_at = datetime.now(timezone.utc)
        raw_results = await asyncio.gather(
            *[ssh_service.run_stress_test(n.ip_address, duration_seconds) for n in nodes],
            return_exceptions=True,
        )
        node_results = [_build_node_result(n, r) for n, r in zip(nodes, raw_results)]

        return StressTestReport(
            started_at=started_at,
            duration_seconds=duration_seconds,
            nodes=node_results,
            any_undervoltage=any(n.undervoltage_detected for n in node_results),
            any_node_unreachable=any(not n.reachable for n in node_results),
            summary=_summarize(node_results),
        )


stress_test_service = StressTestService()
