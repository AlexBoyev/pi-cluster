#!/usr/bin/env bash
# Install ArgoCD on the K3s cluster and create the Pi-Cluster GitOps app.
# Run AFTER install_k3s.sh. Requires sshpass.
set -euo pipefail

SERVER_IP="10.100.102.10"
SSH_USER="admin"
SSH_PASS="admin"
ARGOCD_NODEPORT="30443"
# Update this to your actual Git repo URL
GIT_REPO="${GIT_REPO:-https://github.com/$(git config --get remote.origin.url 2>/dev/null | sed 's|.*github.com[:/]||;s|\.git$||' || echo 'YOUR_USER/pi-cluster')}"

ssh_run() {
  local host=$1; shift
  sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "${SSH_USER}@${host}" "$@"
}

echo "==> [1/5] Creating argocd namespace"
ssh_run "$SERVER_IP" "sudo k3s kubectl create namespace argocd --dry-run=client -o yaml | sudo k3s kubectl apply -f -"

echo "==> [2/5] Installing ArgoCD"
ssh_run "$SERVER_IP" "
  sudo k3s kubectl apply -n argocd \
    -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
"

echo "==> [3/5] Waiting for ArgoCD pods (2-4 min on Pi)..."
ssh_run "$SERVER_IP" "
  sudo k3s kubectl wait --for=condition=available deployment/argocd-server \
    -n argocd --timeout=300s
"

echo "==> [4/5] Exposing ArgoCD UI on NodePort ${ARGOCD_NODEPORT}"
ssh_run "$SERVER_IP" "
  sudo k3s kubectl patch svc argocd-server -n argocd \
    -p '{\"spec\":{\"type\":\"NodePort\",\"ports\":[{\"port\":443,\"targetPort\":8080,\"nodePort\":${ARGOCD_NODEPORT},\"name\":\"https\"}]}}'
"

echo "==> [5/5] Fetching initial admin password"
ARGOCD_PASS=$(ssh_run "$SERVER_IP" \
  "sudo k3s kubectl get secret argocd-initial-admin-secret -n argocd \
   -o jsonpath='{.data.password}' | base64 -d")

echo ""
echo "==> ArgoCD ready."
echo "    URL      : https://${SERVER_IP}:${ARGOCD_NODEPORT}"
echo "    Username : admin"
echo "    Password : ${ARGOCD_PASS}"
echo ""
echo "==> Creating Pi-Cluster GitOps application"
echo "    Git repo : ${GIT_REPO}"

ssh_run "$SERVER_IP" "
cat <<'MANIFEST' | sudo k3s kubectl apply -f -
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: pi-cluster
  namespace: argocd
spec:
  project: default
  source:
    repoURL: ${GIT_REPO}
    targetRevision: HEAD
    path: k8s/apps
  destination:
    server: https://kubernetes.default.svc
    namespace: pi-apps
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
MANIFEST
"

echo "==> Done. ArgoCD is watching k8s/apps/ in your Git repo."
echo "    Push manifests to k8s/apps/ and ArgoCD will apply them automatically."
