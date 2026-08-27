export type NodeStatus = "ONLINE" | "OFFLINE" | "DEGRADED" | "UNKNOWN";

export interface Node {
  id: number;
  name: string;
  ip_address: string;
  status: NodeStatus;
  created_at: string;
  updated_at: string;
}
