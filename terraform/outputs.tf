output "platform_namespace" {
  description = "Kubernetes namespace for the pi-cluster platform"
  value       = kubernetes_namespace.pi_cluster.metadata[0].name
}

output "argocd_namespace" {
  description = "Namespace where ArgoCD is deployed"
  value       = kubernetes_namespace.argocd.metadata[0].name
}

output "argocd_url" {
  description = "ArgoCD UI URL via NodePort on pi-node1"
  value       = "https://10.100.102.10:30443"
}
