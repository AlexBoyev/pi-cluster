export interface PodBasic {
  name: string;
  phase: string;
  containers: string[];
}

export interface PodContainer {
  name: string;
  image: string;
  ready: boolean;
  restart_count: number;
  cpu_request: string | null;
  memory_request: string | null;
  cpu_limit: string | null;
  memory_limit: string | null;
}

export interface PodCondition {
  type: string;
  status: string;
  reason: string | null;
  last_transition: string | null;
}

export interface PodEvent {
  reason: string;
  message: string;
  type: string;
  count: number;
  last_time: string | null;
}

export interface PodDetail {
  name: string;
  namespace: string;
  phase: string;
  node: string | null;
  pod_ip: string | null;
  qos_class: string | null;
  start_time: string | null;
  containers: PodContainer[];
  conditions: PodCondition[];
  events: PodEvent[];
}
