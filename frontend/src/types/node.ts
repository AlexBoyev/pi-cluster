export type NodeStatus = "ONLINE" | "OFFLINE" | "DEGRADED" | "UNKNOWN";

export interface Node {
  id: number;
  name: string;
  ip_address: string;
  status: NodeStatus;
  created_at: string;
  updated_at: string;
}

export interface NodeMetrics {
  cpu_load_1m: number;
  memory_total_bytes: number;
  memory_available_bytes: number;
  memory_percent: number;
  disk_total_bytes: number;
  disk_used_bytes: number;
  disk_percent: number;
  uptime_seconds: number;
  temperature_celsius: number | null;
}

export interface NodeHealth {
  node_id: number;
  node_name: string;
  ip_address: string;
  status: NodeStatus;
  metrics: NodeMetrics | null;
  checked_at: string;
  error: string | null;
}

export interface MetricPoint {
  t: number;
  v: number;
}

export interface NodeMetricsHistory {
  node_name: string;
  period: string;
  cpu_pct: MetricPoint[];
  memory_pct: MetricPoint[];
  disk_pct: MetricPoint[];
  temperature_c: MetricPoint[];
  net_rx_bps: MetricPoint[];
  net_tx_bps: MetricPoint[];
}
