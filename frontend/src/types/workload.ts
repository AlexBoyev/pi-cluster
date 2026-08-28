export type WorkloadStatus = "pending" | "running" | "failed" | "deleted";

export interface Workload {
  id: number;
  name: string;
  namespace: string;
  image: string;
  replicas: number;
  ready_replicas: number;
  target_node: string | null;
  container_port: number | null;
  ingress_host: string | null;
  status: WorkloadStatus;
  created_at: string;
}

export interface NodeCapacity {
  node_name: string;
  cpu_allocatable_m: number;
  cpu_requested_m: number;
  memory_allocatable_mi: number;
  memory_requested_mi: number;
  ready: boolean;
  schedulable: boolean;
}

export interface WorkloadLogs {
  name: string;
  pod_name: string;
  logs: string;
}

export interface WorkloadCreate {
  name: string;
  image: string;
  replicas: number;
  namespace: string;
  target_node?: string | null;
  container_port?: number | null;
  ingress_host?: string | null;
}
