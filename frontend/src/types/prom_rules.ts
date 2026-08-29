export interface AlertRule {
  type: string;
  name: string;
  query: string;
  duration: number;
  labels: Record<string, string>;
  annotations: Record<string, string>;
  state: "inactive" | "pending" | "firing";
  alerts: ActiveAlert[];
}

export interface ActiveAlert {
  labels: Record<string, string>;
  annotations: Record<string, string>;
  state: string;
  activeAt: string;
}

export interface RuleGroup {
  name: string;
  file: string;
  rules: AlertRule[];
}

export interface PrometheusRulesResponse {
  status: string;
  data: {
    groups: RuleGroup[];
  };
}
