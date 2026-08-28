#!/usr/bin/env bash
# Install K3s on all cluster nodes.
# Run from local machine: bash scripts/install_k3s.sh
set -euo pipefail

SERVER_IP="10.100.102.10"
WORKER_IPS=("10.100.102.16" "10.100.102.17" "10.100.102.12")
SSH_USER="admin"
SSH_PASS="admin"

ssh_run() {
  local host=$1; shift
  sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "${SSH_USER}@${host}" "$@"
}

echo "==> [1/4] Installing K3s server on ${SERVER_IP}"
ssh_run "$SERVER_IP" "
  curl -sfL https://get.k3s.io | \
    INSTALL_K3S_EXEC='server --disable traefik --write-kubeconfig-mode 644' sh -
  sleep 10
  sudo systemctl enable --now k3s
"

echo "==> [2/4] Fetching node token"
TOKEN=$(ssh_run "$SERVER_IP" "sudo cat /var/lib/rancher/k3s/server/node-token")
echo "    Token: ${TOKEN:0:20}..."

echo "==> [3/4] Installing K3s agents"
for IP in "${WORKER_IPS[@]}"; do
  echo "    → ${IP}"
  ssh_run "$IP" "
    curl -sfL https://get.k3s.io | \
      K3S_URL='https://${SERVER_IP}:6443' \
      K3S_TOKEN='${TOKEN}' sh -
    sudo systemctl enable --now k3s-agent
  " &
done
wait
echo "    Waiting 20s for agents to register..."
sleep 20

echo "==> [4/4] Verifying cluster"
ssh_run "$SERVER_IP" "sudo k3s kubectl get nodes -o wide"

echo ""
echo "==> K3s cluster ready."
echo "    API server : https://${SERVER_IP}:6443"
echo "    To use kubectl locally, copy /etc/rancher/k3s/k3s.yaml from pi-node1"
echo "    and replace '127.0.0.1' with '${SERVER_IP}'"
