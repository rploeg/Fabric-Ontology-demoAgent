#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Build, push, and deploy the Zava MQTT Simulator to AKS/AIO
# =============================================================================
# Usage:
#   ./scripts/deploy.sh              # full pipeline: build → push → deploy
#   ./scripts/deploy.sh build        # docker build only
#   ./scripts/deploy.sh push         # push to ACR only (assumes image exists)
#   ./scripts/deploy.sh deploy       # k8s apply only (assumes image in ACR)
#   ./scripts/deploy.sh configmap    # update ConfigMap only
#
# Configuration: set variables in .env (see .env.example) or export them.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load .env if present
ENV_FILE="$PROJECT_DIR/.env"
if [[ -f "$ENV_FILE" ]]; then
  echo "📄 Loading config from $ENV_FILE"
  set -a
  # shellcheck source=/dev/null
  source "$ENV_FILE"
  set +a
fi

# --- Required variables ---
ACR_NAME="${ACR_NAME:?Set ACR_NAME in .env or environment (e.g. myacr)}"
AKS_RG="${AKS_RG:?Set AKS_RG in .env or environment (e.g. my-resource-group)}"
AKS_NAME="${AKS_NAME:?Set AKS_NAME in .env or environment (e.g. my-aks-cluster)}"

# --- Optional variables ---
IMAGE_NAME="${IMAGE_NAME:-zava-simulator}"
IMAGE_TAG="${IMAGE_TAG:-$(git -C "$PROJECT_DIR" rev-parse --short HEAD 2>/dev/null || echo 'latest')}"
K8S_NAMESPACE="${K8S_NAMESPACE:-zava-simulator}"
FULL_IMAGE="$ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG"

# --- Helpers ---
info()  { echo "▶ $*"; }
ok()    { echo "✅ $*"; }
fail()  { echo "❌ $*" >&2; exit 1; }

check_prereqs() {
  for cmd in docker az kubectl; do
    command -v "$cmd" >/dev/null 2>&1 || fail "$cmd is required but not found"
  done
}

# --- Steps ---

do_build() {
  info "Building Docker image: $FULL_IMAGE"
  docker build -t "$FULL_IMAGE" "$PROJECT_DIR"
  # Also tag as :latest for convenience
  docker tag "$FULL_IMAGE" "$ACR_NAME.azurecr.io/$IMAGE_NAME:latest"
  ok "Image built: $FULL_IMAGE"
}

do_push() {
  info "Logging in to ACR: $ACR_NAME"
  az acr login --name "$ACR_NAME" --only-show-errors
  info "Pushing $FULL_IMAGE"
  docker push "$FULL_IMAGE"
  docker push "$ACR_NAME.azurecr.io/$IMAGE_NAME:latest"
  ok "Pushed to $ACR_NAME.azurecr.io"
}

do_configmap() {
  info "Updating ConfigMap from simulator-config.yaml"
  kubectl create configmap zava-simulator-config \
    --from-file=simulator-config.yaml="$PROJECT_DIR/simulator-config.yaml" \
    -n "$K8S_NAMESPACE" \
    --dry-run=client -o yaml | kubectl apply -f -
  ok "ConfigMap updated"
}

do_deploy() {
  info "Ensuring kubectl context points to $AKS_NAME"
  az aks get-credentials \
    --resource-group "$AKS_RG" \
    --name "$AKS_NAME" \
    --overwrite-existing \
    --only-show-errors

  info "Applying K8s manifests"
  kubectl apply -k "$PROJECT_DIR/k8s/"

  # Apply broker auth (idempotent — safe to re-apply)
  info "Applying broker auth (BrokerAuthentication + BrokerAuthorization)"
  kubectl apply -f "$PROJECT_DIR/k8s/broker-auth.yaml" 2>/dev/null || \
    echo "  ⚠️  broker-auth.yaml skipped (CRDs may not be installed yet)"

  do_configmap

  info "Updating image to $FULL_IMAGE"
  kubectl set image deployment/zava-simulator \
    simulator="$FULL_IMAGE" \
    -n "$K8S_NAMESPACE"

  info "Waiting for rollout..."
  kubectl rollout status deployment/zava-simulator \
    -n "$K8S_NAMESPACE" \
    --timeout=120s

  ok "Deployed $FULL_IMAGE to $AKS_NAME ($K8S_NAMESPACE)"
  echo ""
  info "Pod status:"
  kubectl get pods -n "$K8S_NAMESPACE" -l app=zava-simulator
  echo ""
  info "Tail logs with: kubectl logs -n $K8S_NAMESPACE -l app=zava-simulator -f"
}

# --- Main ---

check_prereqs

STEP="${1:-all}"

case "$STEP" in
  build)     do_build ;;
  push)      do_push ;;
  configmap) do_configmap ;;
  deploy)    do_deploy ;;
  all)
    do_build
    do_push
    do_deploy
    ;;
  *)
    echo "Usage: $0 {all|build|push|configmap|deploy}"
    exit 1
    ;;
esac
