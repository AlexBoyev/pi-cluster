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
  env_vars: Record<string, string>;
  cpu_limit: string;
  memory_limit: string;
  liveness_path: string | null;
  readiness_path: string | null;
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

export interface WorkloadEvent {
  type: string;
  reason: string;
  message: string;
  object_name: string;
  count: number;
  first_time: string | null;
  last_time: string | null;
}

export interface PodInfo {
  name: string;
  phase: string;
  node: string | null;
  pod_ip: string | null;
  ready: number;
  total: number;
  started_at: string | null;
}

export interface WorkloadMetrics {
  name: string;
  cpu_cores: number;
  cpu_limit_cores: number;
  memory_bytes: number;
  memory_limit_bytes: number;
  pod_count: number;
  available: boolean;
}

export interface WorkloadCreate {
  name: string;
  image: string;
  replicas: number;
  namespace: string;
  target_node?: string | null;
  container_port?: number | null;
  ingress_host?: string | null;
  env_vars?: Record<string, string>;
  cpu_limit?: string;
  memory_limit?: string;
  liveness_path?: string | null;
  readiness_path?: string | null;
}
