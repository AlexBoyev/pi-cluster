import type { AlertHistoryEntry } from "../types/alert";
import { apiFetch } from "./client";

export const getAlertHistory = (
  limit = 100,
  offset = 0,
  severity?: string,
  state?: string,
) => {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (severity) params.set("severity", severity);
  if (state) params.set("state", state);
  return apiFetch<AlertHistoryEntry[]>(`/alert-history/?${params}`);
};
