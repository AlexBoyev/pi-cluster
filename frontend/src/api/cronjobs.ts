import type { CronJobCreate, CronJobInfo, JobRun } from "../types/cronjob";
import { apiFetch } from "./client";

export const listCronJobs = (namespace?: string) =>
  apiFetch<CronJobInfo[]>(`/cronjobs/${namespace ? `?namespace=${encodeURIComponent(namespace)}` : ""}`);

export const createCronJob = (data: CronJobCreate) =>
  apiFetch<CronJobInfo>("/cronjobs/", { method: "POST", body: JSON.stringify(data) });

export const suspendCronJob = (name: string, namespace = "pi-apps") =>
  apiFetch<CronJobInfo>(`/cronjobs/${encodeURIComponent(name)}/suspend?namespace=${encodeURIComponent(namespace)}`, { method: "PATCH" });

export const resumeCronJob = (name: string, namespace = "pi-apps") =>
  apiFetch<CronJobInfo>(`/cronjobs/${encodeURIComponent(name)}/resume?namespace=${encodeURIComponent(namespace)}`, { method: "PATCH" });

export const listCronJobRuns = (name: string, namespace = "pi-apps") =>
  apiFetch<JobRun[]>(`/cronjobs/${encodeURIComponent(name)}/jobs?namespace=${encodeURIComponent(namespace)}`);

export const deleteCronJob = (name: string, namespace = "pi-apps") =>
  apiFetch<void>(`/cronjobs/${encodeURIComponent(name)}?namespace=${encodeURIComponent(namespace)}`, { method: "DELETE" });
