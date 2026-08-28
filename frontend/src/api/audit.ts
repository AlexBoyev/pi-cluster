import type { AuditLog } from "../types/audit";
import { apiFetch } from "./client";

export const listAuditLogs = (limit = 100, offset = 0) =>
  apiFetch<AuditLog[]>(`/audit/?limit=${limit}&offset=${offset}`);
