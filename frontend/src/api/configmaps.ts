import type { ConfigMapDetail, ConfigMapSummary } from "../types/configmap";
import { apiFetch } from "./client";

export const listConfigMaps = (namespace = "pi-apps") =>
  apiFetch<ConfigMapSummary[]>(`/configmaps/?namespace=${encodeURIComponent(namespace)}`);

export const getConfigMap = (name: string, namespace = "pi-apps") =>
  apiFetch<ConfigMapDetail>(`/configmaps/${encodeURIComponent(name)}?namespace=${encodeURIComponent(namespace)}`);

export const createConfigMap = (name: string, namespace: string, data: Record<string, string>) =>
  apiFetch<ConfigMapDetail>("/configmaps/", {
    method: "POST",
    body: JSON.stringify({ name, namespace, data }),
  });

export const updateConfigMap = (name: string, namespace: string, data: Record<string, string>) =>
  apiFetch<ConfigMapDetail>(`/configmaps/${encodeURIComponent(name)}?namespace=${encodeURIComponent(namespace)}`, {
    method: "PUT",
    body: JSON.stringify({ data }),
  });

export const deleteConfigMap = (name: string, namespace = "pi-apps") =>
  apiFetch<void>(`/configmaps/${encodeURIComponent(name)}?namespace=${encodeURIComponent(namespace)}`, {
    method: "DELETE",
  });
