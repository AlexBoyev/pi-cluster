export interface CronJobInfo {
  name: string;
  namespace: string;
  schedule: string;
  suspended: boolean;
  active_jobs: number;
  last_schedule_time: string | null;
  image: string;
  created_at: string | null;
}

export interface CronJobCreate {
  name: string;
  namespace: string;
  schedule: string;
  image: string;
  command: string[];
  env_vars: Record<string, string>;
}

export interface JobRun {
  name: string;
  succeeded: number;
  failed: number;
  active: number;
  start_time: string | null;
  completion_time: string | null;
}
