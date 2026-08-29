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
