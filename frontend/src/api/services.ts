import type { IngressInfo, ServiceInfo } from "../types/service";
import { apiFetch } from "./client";

export const listServices = (namespace?: string) =>
  apiFetch<ServiceInfo[]>(`/services${namespace ? `?namespace=${encodeURIComponent(namespace)}` : ""}`);

export const listIngresses = (namespace?: string) =>
  apiFetch<IngressInfo[]>(`/ingresses${namespace ? `?namespace=${encodeURIComponent(namespace)}` : ""}`);
