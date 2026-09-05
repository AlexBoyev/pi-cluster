import { apiFetch } from "./client";
import type { PrometheusRulesResponse } from "../types/prom_rules";

export function getAlertRules(): Promise<PrometheusRulesResponse> {
  return apiFetch("/prometheus/rules");
}

export interface RuleFormData {
  group: string;
  alert: string;
  expr: string;
  for: string;
  severity: string;
  summary: string;
  description: string;
}

export function createRule(data: RuleFormData): Promise<{ detail: string }> {
  return apiFetch("/prometheus/rules", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateRule(
  group: string,
  alert: string,
  data: Omit<RuleFormData, "group" | "alert">
): Promise<{ detail: string }> {
  return apiFetch(`/prometheus/rules/${encodeURIComponent(group)}/${encodeURIComponent(alert)}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteRule(group: string, alert: string): Promise<{ detail: string }> {
  return apiFetch(`/prometheus/rules/${encodeURIComponent(group)}/${encodeURIComponent(alert)}`, {
    method: "DELETE",
  });
}
