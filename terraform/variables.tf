variable "kubeconfig_path" {
  description = "Path to kubeconfig for the K3s cluster"
  type        = string
  default     = "~/.kube/pi-cluster-config"
}

variable "platform_namespace" {
  description = "Kubernetes namespace for the pi-cluster platform"
  type        = string
  default     = "pi-cluster"
}

variable "db_password" {
  description = "PostgreSQL password"
  type        = string
  sensitive   = true
}

variable "redis_password" {
  description = "Redis password"
  type        = string
  sensitive   = true
}

variable "jwt_secret" {
  description = "JWT signing secret"
  type        = string
  sensitive   = true
}

variable "prometheus_url" {
  description = "Internal Prometheus URL"
  type        = string
  default     = "http://prometheus:9090"
}
