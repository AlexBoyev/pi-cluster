import { apiFetch } from "./client";
import type { PVCCreate, PVCInfo, PVInfo, StorageClassInfo } from "../types/storage";

export function listPVCs(namespace?: string): Promise<PVCInfo[]> {
  const q = namespace ? `?namespace=${encodeURIComponent(namespace)}` : "";
  return apiFetch(`/storage/pvcs${q}`);
}

export function createPVC(data: PVCCreate): Promise<PVCInfo> {
  return apiFetch("/storage/pvcs", { method: "POST", body: JSON.stringify(data) });
}

export function deletePVC(namespace: string, name: string): Promise<void> {
  return apiFetch(`/storage/pvcs/${encodeURIComponent(namespace)}/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });
}

export function listPVs(): Promise<PVInfo[]> {
  return apiFetch("/storage/pvs");
}

export function listStorageClasses(): Promise<StorageClassInfo[]> {
  return apiFetch("/storage/classes");
}
