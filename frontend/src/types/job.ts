export interface JobInfo {
  name: string;
  namespace: string;
  state: "running" | "succeeded" | "failed" | "unknown";
  active: number;
  succeeded: number;
  failed: number;
  cron_job: string | null;
  start_time: string | null;
  completion_time: string | null;
  created_at: string | null;
}
