import { apiFetch } from "./client";
import type { ClusterRoleBindingInfo, ClusterRoleInfo, ServiceAccountInfo } from "../types/rbac";

export function listClusterRoles(hideSystem = true): Promise<ClusterRoleInfo[]> {
  return apiFetch(`/rbac/clusterroles?hide_system=${hideSystem}`);
}

export function listClusterRoleBindings(hideSystem = true): Promise<ClusterRoleBindingInfo[]> {
  return apiFetch(`/rbac/clusterrolebindings?hide_system=${hideSystem}`);
}

export function listServiceAccounts(namespace?: string): Promise<ServiceAccountInfo[]> {
  const q = namespace ? `?namespace=${encodeURIComponent(namespace)}` : "";
  return apiFetch(`/rbac/serviceaccounts${q}`);
}
