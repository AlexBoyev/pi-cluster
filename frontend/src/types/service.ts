export interface ServicePort {
  port: number;
  target_port: string | null;
  node_port: number | null;
  protocol: string;
}

export interface ServiceInfo {
  name: string;
  namespace: string;
  type: string;
  cluster_ip: string | null;
  external_ip: string | null;
  ports: ServicePort[];
  selector: Record<string, string>;
  created_at: string | null;
}

export interface IngressPath {
  path: string;
  backend_service: string | null;
  backend_port: number | null;
}

export interface IngressRule {
  host: string | null;
  paths: IngressPath[];
}

export interface IngressInfo {
  name: string;
  namespace: string;
  rules: IngressRule[];
  tls_hosts: string[];
  ingress_class: string | null;
  created_at: string | null;
}
