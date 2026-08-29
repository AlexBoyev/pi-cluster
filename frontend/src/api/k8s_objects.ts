import { apiFetch } from "./client";
import type { DaemonSetInfo, StatefulSetInfo } from "../types/k8s_objects";

export function listStatefulSets(namespace?: string): Promise<StatefulSetInfo[]> {
  const q = namespace ? `?namespace=${encodeURIComponent(namespace)}` : "";
  return apiFetch(`/objects/statefulsets${q}`);
}

export function listDaemonSets(namespace?: string): Promise<DaemonSetInfo[]> {
  const q = namespace ? `?namespace=${encodeURIComponent(namespace)}` : "";
  return apiFetch(`/objects/daemonsets${q}`);
}
