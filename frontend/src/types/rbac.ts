export interface PolicyRule {
  api_groups: string[];
  resources: string[];
  verbs: string[];
}

export interface ClusterRoleInfo {
  name: string;
  rules_count: number;
  rules: PolicyRule[];
  created_at: string | null;
}

export interface RoleSubject {
  kind: string;
  name: string;
  namespace: string | null;
}

export interface ClusterRoleBindingInfo {
  name: string;
  role_kind: string | null;
  role_name: string | null;
  subjects: RoleSubject[];
  created_at: string | null;
}

export interface ServiceAccountInfo {
  name: string;
  namespace: string | null;
  secrets_count: number;
  created_at: string | null;
}
