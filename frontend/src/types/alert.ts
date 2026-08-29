export interface Alert {
  name: string;
  severity: "critical" | "warning" | "info";
  state: "firing" | "pending";
  node_name: string | null;
  summary: string;
  description: string;
  fired_at: string;
  duration_seconds: number;
}

export interface AlertHistoryEntry {
  id: number;
  alert_name: string;
  severity: string;
  node_name: string | null;
  instance: string | null;
  summary: string | null;
  fired_at: string;
  resolved_at: string | null;
}
