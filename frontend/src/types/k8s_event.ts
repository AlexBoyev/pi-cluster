export interface ClusterEvent {
  namespace: string;
  type: string;
  reason: string;
  message: string;
  object_kind: string;
  object_name: string;
  count: number;
  first_time: string | null;
  last_time: string | null;
}
