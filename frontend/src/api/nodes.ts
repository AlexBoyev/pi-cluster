import type { Node, NodeMetricsHistory } from "../types/node";
import { apiFetch } from "./client";

export const getNodes = () => apiFetch<Node[]>("/nodes/");
export const getNode = (id: number) => apiFetch<Node>(`/nodes/${id}`);
export const getNodeMetricsHistory = (id: number, period: "1h" | "6h" | "24h") =>
  apiFetch<NodeMetricsHistory>(`/nodes/${id}/metrics/history?period=${period}`);
