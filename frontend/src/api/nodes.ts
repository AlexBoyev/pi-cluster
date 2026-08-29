import type { Node, NodeMetricsHistory } from "../types/node";
import { apiFetch } from "./client";

export const getNodes = () => apiFetch<Node[]>("/nodes/");
export const getNode = (id: number) => apiFetch<Node>(`/nodes/${id}`);
export const getNodeMetricsHistory = (id: number, period: "1h" | "6h" | "24h") =>
  apiFetch<NodeMetricsHistory>(`/nodes/${id}/metrics/history?period=${period}`);
export const restartNode  = (id: number) => apiFetch<{ status: string; node: string }>(`/nodes/${id}/restart`,  { method: "POST" });
export const shutdownNode = (id: number) => apiFetch<{ status: string; node: string }>(`/nodes/${id}/shutdown`, { method: "POST" });
export const restartAllNodes  = () => apiFetch<{ status: string; count: number }>("/nodes/all/restart",  { method: "POST" });
export const shutdownAllNodes = () => apiFetch<{ status: string; count: number }>("/nodes/all/shutdown", { method: "POST" });
