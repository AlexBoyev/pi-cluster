import { apiFetch } from "./client";
import type { PrometheusRulesResponse } from "../types/prom_rules";

export function getAlertRules(): Promise<PrometheusRulesResponse> {
  return apiFetch("/prometheus/rules");
}
