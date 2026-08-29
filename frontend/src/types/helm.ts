export interface HelmRelease {
  name: string;
  namespace: string;
  chart: string;
  chart_version: string | null;
  app_version: string | null;
  status: string;
  revision: number;
  description: string | null;
  first_deployed: string | null;
  last_deployed: string | null;
}
