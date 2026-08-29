export interface PVCInfo {
  name: string;
  namespace: string;
  status: string;
  capacity: string | null;
  storage_class: string | null;
  access_modes: string[];
  volume_name: string | null;
  created_at: string | null;
}

export interface PVInfo {
  name: string;
  status: string;
  capacity: string | null;
  access_modes: string[];
  storage_class: string | null;
  reclaim_policy: string | null;
  claim_namespace: string | null;
  claim_name: string | null;
  created_at: string | null;
}

export interface PVCCreate {
  name: string;
  namespace: string;
  storage_class: string;
  access_modes: string[];
  size: string;
}

export interface StorageClassInfo {
  name: string;
  provisioner: string;
  reclaim_policy: string;
  binding_mode: string;
  is_default: boolean;
  created_at: string | null;
}
