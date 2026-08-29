export interface StatefulSetInfo {
  name: string;
  namespace: string;
  replicas: number;
  ready_replicas: number;
  service_name: string | null;
  images: string[];
  created_at: string | null;
}

export interface DaemonSetInfo {
  name: string;
  namespace: string;
  desired: number;
  current: number;
  ready: number;
  available: number;
  images: string[];
  created_at: string | null;
}
