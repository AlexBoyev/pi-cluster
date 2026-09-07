resource "kubernetes_namespace" "argocd" {
  metadata {
    name = "argocd"
    labels = {
      "app.kubernetes.io/managed-by" = "terraform"
    }
  }
}

resource "helm_release" "argocd" {
  name       = "argocd"
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"
  version    = "6.7.14"
  namespace  = kubernetes_namespace.argocd.metadata[0].name

  set {
    name  = "server.service.type"
    value = "NodePort"
  }

  set {
    name  = "server.service.nodePortHttps"
    value = "30443"
  }

  set {
    name  = "configs.params.server\\.insecure"
    value = "true"
  }

  depends_on = [kubernetes_namespace.argocd]
}

resource "kubernetes_manifest" "pi_cluster_app" {
  # NAME/NAMESPACE CORRECTED 2026-09-07: this resource never actually
  # matched the live Application - the real one (verified via
  # `kubectl get application -n argocd`) is named "pi-cluster" with
  # destination namespace "pi-apps", not "pi-cluster-apps"/"pi-cluster".
  # It was created some other way, never through this Terraform file or
  # ansible/playbooks/argocd.yml (which only ever does a one-time
  # `kubectl apply`, never creates a watching Application resource either)
  # - the actual origin is unknown. Also missing `directory.recurse`,
  # which meant every household service (Wallabag, Vikunja, Paperless,
  # and Firefly on first deploy) was silently NEVER GitOps-managed despite
  # every README claiming otherwise - all of them were only ever reachable
  # via the manual `kubectl apply -f k8s/apps/<name>/` fallback each one
  # documents. See docs/decisions.md for the full incident.
  manifest = {
    apiVersion = "argoproj.io/v1alpha1"
    kind       = "Application"
    metadata = {
      name      = "pi-cluster"
      namespace = "argocd"
    }
    spec = {
      project = "default"
      source = {
        repoURL        = "https://github.com/AlexBoyev/pi-cluster.git"
        targetRevision = "master"
        path           = "k8s/apps"
        directory = {
          recurse = true
        }
      }
      destination = {
        server    = "https://kubernetes.default.svc"
        namespace = "pi-apps"
      }
      syncPolicy = {
        automated = {
          prune    = true
          selfHeal = true
        }
        syncOptions = [
          "CreateNamespace=true"
        ]
      }
    }
  }

  depends_on = [helm_release.argocd]
}
