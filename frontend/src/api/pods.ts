import { apiFetch } from "./client";
import type { PodBasic, PodDetail } from "../types/pod";

export function listPods(namespace: string): Promise<PodBasic[]> {
  return apiFetch(`/pods/?namespace=${encodeURIComponent(namespace)}`);
}

export function getPodDetail(namespace: string, name: string): Promise<PodDetail> {
  return apiFetch(`/pods/${encodeURIComponent(namespace)}/${encodeURIComponent(name)}`);
}
