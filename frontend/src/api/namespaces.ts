import type { NamespaceInfo } from "../types/namespace";
import { apiFetch } from "./client";

export const listNamespaces = () => apiFetch<NamespaceInfo[]>("/namespaces/");

export const createNamespace = (name: string) =>
  apiFetch<NamespaceInfo>("/namespaces/", { method: "POST", body: JSON.stringify({ name }) });

export const deleteNamespace = (name: string) =>
  apiFetch<void>(`/namespaces/${name}`, { method: "DELETE" });
