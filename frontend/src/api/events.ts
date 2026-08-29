import type { ClusterEvent } from "../types/k8s_event";
import { apiFetch } from "./client";

export const getClusterEvents = (namespace?: string, eventType?: string, limit = 200) => {
  const params = new URLSearchParams({ limit: String(limit) });
  if (namespace) params.set("namespace", namespace);
  if (eventType) params.set("event_type", eventType);
  return apiFetch<ClusterEvent[]>(`/events/?${params}`);
};
