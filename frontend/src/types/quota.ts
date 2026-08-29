export interface QuotaResource {
  resource: string;
  hard: string;
  used: string;
}

export interface ResourceQuotaInfo {
  name: string;
  namespace: string;
  resources: QuotaResource[];
  created_at: string | null;
}

export interface LimitRangeItem {
  type: string;
  resource: string;
  max: string | null;
  min: string | null;
  default: string | null;
  default_request: string | null;
}

export interface LimitRangeInfo {
  name: string;
  namespace: string;
  limits: LimitRangeItem[];
  created_at: string | null;
}
