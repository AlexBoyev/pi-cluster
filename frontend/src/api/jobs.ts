import { apiFetch } from "./client";
import type { JobInfo } from "../types/job";

export function listJobs(namespace?: string): Promise<JobInfo[]> {
  const q = namespace ? `?namespace=${encodeURIComponent(namespace)}` : "";
  return apiFetch(`/jobs/${q}`);
}
