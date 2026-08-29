import type { AuditLog } from "../types/audit";
import { apiFetch } from "./client";

export const listAuditLogs = (
  limit = 100,
  offset = 0,
  status?: string,
  resource_type?: string,
) => {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (status) params.set("status", status);
  if (resource_type) params.set("resource_type", resource_type);
  return apiFetch<AuditLog[]>(`/audit/?${params}`);
};
