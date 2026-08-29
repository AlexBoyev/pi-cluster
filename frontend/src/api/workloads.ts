import type { NodeCapacity, PodInfo, Workload, WorkloadCreate, WorkloadEvent, WorkloadHistory, WorkloadLogs, WorkloadMetrics } from "../types/workload";
import { apiFetch } from "./client";

export const listWorkloads = () => apiFetch<Workload[]>("/workloads/");
export const getCapacity = () => apiFetch<NodeCapacity[]>("/workloads/capacity");
export const createWorkload = (data: WorkloadCreate) =>
  apiFetch<Workload>("/workloads/", { method: "POST", body: JSON.stringify(data) });
export const deleteWorkload = (name: string) =>
  apiFetch<{ deleted: string }>(`/workloads/${name}`, { method: "DELETE" });
export const scaleWorkload = (name: string, replicas: number) =>
  apiFetch<Workload>(`/workloads/${name}/scale`, {
    method: "PATCH",
    body: JSON.stringify({ replicas }),
  });
export const updateWorkloadImage = (name: string, image: string) =>
  apiFetch<Workload>(`/workloads/${name}/image`, {
    method: "PATCH",
    body: JSON.stringify({ image }),
  });
export const updateWorkloadResources = (name: string, cpu_limit: string, memory_limit: string) =>
  apiFetch<Workload>(`/workloads/${name}/resources`, {
    method: "PATCH",
    body: JSON.stringify({ cpu_limit, memory_limit }),
  });
export const updateWorkloadEnv = (name: string, env_vars: Record<string, string>) =>
  apiFetch<Workload>(`/workloads/${name}/env`, {
    method: "PATCH",
    body: JSON.stringify({ env_vars }),
  });
export const getWorkloadPods = (name: string) =>
  apiFetch<PodInfo[]>(`/workloads/${name}/pods`);
export const getWorkloadEvents = (name: string) =>
  apiFetch<WorkloadEvent[]>(`/workloads/${name}/events`);
export const getWorkloadLogs = (name: string, tail = 100) =>
  apiFetch<WorkloadLogs>(`/workloads/${name}/logs?tail=${tail}`);
export const updateWorkloadProbes = (name: string, liveness_path: string | null, readiness_path: string | null) =>
  apiFetch<Workload>(`/workloads/${name}/probes`, {
    method: "PATCH",
    body: JSON.stringify({ liveness_path, readiness_path }),
  });
export const restartWorkload = (name: string) =>
  apiFetch<{ restarted: string }>(`/workloads/${name}/restart`, { method: "POST" });
export const getWorkloadMetrics = (name: string) =>
  apiFetch<WorkloadMetrics>(`/workloads/${name}/metrics`);
export const drainNode = (name: string) =>
  apiFetch<{ drained: string; evicted: number }>(`/workloads/nodes/${name}/drain`, { method: "POST" });
export const cordonNode = (name: string) =>
  apiFetch<{ cordoned: string }>(`/workloads/nodes/${name}/cordon`, { method: "POST" });
export const uncordonNode = (name: string) =>
  apiFetch<{ uncordoned: string }>(`/workloads/nodes/${name}/cordon`, { method: "DELETE" });
export const getWorkloadHistory = (name: string) =>
  apiFetch<WorkloadHistory>(`/workloads/${name}/history`);
export const rollbackWorkload = (name: string, revision: number) =>
  apiFetch<Workload>(`/workloads/${name}/rollback`, {
    method: "POST",
    body: JSON.stringify({ revision }),
  });
