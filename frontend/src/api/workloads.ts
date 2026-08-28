import type { NodeCapacity, Workload, WorkloadCreate, WorkloadEvent, WorkloadLogs } from "../types/workload";
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
export const getWorkloadEvents = (name: string) =>
  apiFetch<WorkloadEvent[]>(`/workloads/${name}/events`);
export const getWorkloadLogs = (name: string, tail = 100) =>
  apiFetch<WorkloadLogs>(`/workloads/${name}/logs?tail=${tail}`);
export const cordonNode = (name: string) =>
  apiFetch<{ cordoned: string }>(`/workloads/nodes/${name}/cordon`, { method: "POST" });
export const uncordonNode = (name: string) =>
  apiFetch<{ uncordoned: string }>(`/workloads/nodes/${name}/cordon`, { method: "DELETE" });
