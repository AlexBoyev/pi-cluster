export interface AuditLog {
  id: number;
  action: string;
  resource_type: string;
  resource_name: string;
  actor: string;
  status: "success" | "failure";
  detail: string | null;
  created_at: string;
}
