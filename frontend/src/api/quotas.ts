import { apiFetch } from "./client";
import type { LimitRangeInfo, ResourceQuotaInfo } from "../types/quota";

export function listResourceQuotas(namespace?: string): Promise<ResourceQuotaInfo[]> {
  const q = namespace ? `?namespace=${encodeURIComponent(namespace)}` : "";
  return apiFetch(`/quotas/resourcequotas${q}`);
}

export function listLimitRanges(namespace?: string): Promise<LimitRangeInfo[]> {
  const q = namespace ? `?namespace=${encodeURIComponent(namespace)}` : "";
  return apiFetch(`/quotas/limitranges${q}`);
}
