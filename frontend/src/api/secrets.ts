import type { SecretDetail, SecretSummary } from "../types/secret";
import { apiFetch } from "./client";

export const listSecrets = (namespace = "pi-apps") =>
  apiFetch<SecretSummary[]>(`/secrets/?namespace=${encodeURIComponent(namespace)}`);

export const getSecret = (name: string, namespace = "pi-apps") =>
  apiFetch<SecretDetail>(`/secrets/${encodeURIComponent(name)}?namespace=${encodeURIComponent(namespace)}`);

export const createSecret = (name: string, namespace: string, data: Record<string, string>, type = "Opaque") =>
  apiFetch<SecretSummary>("/secrets/", {
    method: "POST",
    body: JSON.stringify({ name, namespace, data, type }),
  });

export const updateSecret = (name: string, namespace: string, data: Record<string, string>) =>
  apiFetch<SecretSummary>(`/secrets/${encodeURIComponent(name)}?namespace=${encodeURIComponent(namespace)}`, {
    method: "PUT",
    body: JSON.stringify({ data }),
  });

export const deleteSecret = (name: string, namespace = "pi-apps") =>
  apiFetch<void>(`/secrets/${encodeURIComponent(name)}?namespace=${encodeURIComponent(namespace)}`, {
    method: "DELETE",
  });
