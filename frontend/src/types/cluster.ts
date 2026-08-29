export interface NodeCapacityDetail {
  node_name: string;
  cpu_allocatable_cores: number;
  cpu_requested_cores: number;
  cpu_used_cores: number;
  memory_allocatable_bytes: number;
  memory_requested_bytes: number;
  memory_used_bytes: number;
  ready: boolean;
  schedulable: boolean;
}

export interface ClusterCapacity {
  cpu_allocatable_cores: number;
  cpu_requested_cores: number;
  cpu_used_cores: number;
  memory_allocatable_bytes: number;
  memory_requested_bytes: number;
  memory_used_bytes: number;
  nodes: NodeCapacityDetail[];
}
