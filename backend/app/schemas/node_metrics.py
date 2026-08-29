from pydantic import BaseModel


class MetricPoint(BaseModel):
    t: float  # unix timestamp
    v: float  # metric value


class NodeMetricsHistory(BaseModel):
    node_name: str
    period: str
    cpu_pct: list[MetricPoint]
    memory_pct: list[MetricPoint]
    disk_pct: list[MetricPoint]
    temperature_c: list[MetricPoint]
    net_rx_bps: list[MetricPoint]
    net_tx_bps: list[MetricPoint]
