from datetime import datetime

from pydantic import BaseModel, Field


class StressTestRequest(BaseModel):
    duration_seconds: int = Field(default=30, ge=10, le=120)


class ThrottleReading(BaseModel):
    elapsed_seconds: float
    throttled_hex: str
    undervoltage_now: bool
    freq_capped_now: bool
    throttled_now: bool
    undervoltage_occurred: bool
    throttled_occurred: bool
    temp_celsius: float | None
    volts: float | None


class NodeStressResult(BaseModel):
    node_name: str
    ip_address: str
    reachable: bool
    error: str | None = None
    ncores: int | None = None
    baseline: ThrottleReading | None = None
    samples: list[ThrottleReading] = []
    final: ThrottleReading | None = None
    max_temp_celsius: float | None = None
    min_volts: float | None = None
    undervoltage_detected: bool = False
    throttled_detected: bool = False
    verdict: str = "unknown"


class StressTestReport(BaseModel):
    started_at: datetime
    duration_seconds: int
    nodes: list[NodeStressResult]
    any_undervoltage: bool
    any_node_unreachable: bool
    summary: str
