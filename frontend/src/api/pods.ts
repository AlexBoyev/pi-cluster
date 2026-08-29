import { apiFetch } from "./client";
import type { PodDetail } from "../types/pod";

export function getPodDetail(namespace: string, name: string): Promise<PodDetail> {
  return apiFetch(`/pods/${encodeURIComponent(namespace)}/${encodeURIComponent(name)}`);
}
