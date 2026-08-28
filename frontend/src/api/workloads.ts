import type { NodeCapacity, Workload, WorkloadCreate } from "../types/workload";
import { apiFetch } from "./client";

export const listWorkloads = () => apiFetch<Workload[]>("/workloads/");
export const getCapacity = () => apiFetch<NodeCapacity[]>("/workloads/capacity");
export const createWorkload = (data: WorkloadCreate) =>
  apiFetch<Workload>("/workloads/", { method: "POST", body: JSON.stringify(data) });
export const deleteWorkload = (name: string) =>
  apiFetch<{ deleted: string }>(`/workloads/${name}`, { method: "DELETE" });
export const cordonNode = (name: string) =>
  apiFetch<{ cordoned: string }>(`/workloads/nodes/${name}/cordon`, { method: "POST" });
export const uncordonNode = (name: string) =>
  apiFetch<{ uncordoned: string }>(`/workloads/nodes/${name}/cordon`, { method: "DELETE" });
