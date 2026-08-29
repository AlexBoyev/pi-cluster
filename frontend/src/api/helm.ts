import { apiFetch } from "./client";
import type { HelmRelease } from "../types/helm";

export function listHelmReleases(namespace?: string): Promise<HelmRelease[]> {
  const q = namespace ? `?namespace=${encodeURIComponent(namespace)}` : "";
  return apiFetch(`/helm/releases${q}`);
}
