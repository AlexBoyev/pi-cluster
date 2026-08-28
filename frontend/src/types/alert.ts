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
