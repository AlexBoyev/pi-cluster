export interface SecretSummary {
  name: string;
  namespace: string;
  type: string;
  data_keys: string[];
  created_at: string | null;
}

export interface SecretDetail {
  name: string;
  namespace: string;
  type: string;
  data: Record<string, string>;
  created_at: string | null;
}
