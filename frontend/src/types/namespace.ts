export interface NamespaceInfo {
  name: string;
  status: string;
  created_at: string | null;
  labels: Record<string, string>;
}
