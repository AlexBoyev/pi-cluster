export interface ConfigMapSummary {
  name: string;
  namespace: string;
  data_keys: string[];
  created_at: string | null;
}

export interface ConfigMapDetail {
  name: string;
  namespace: string;
  data: Record<string, string>;
  created_at: string | null;
}
