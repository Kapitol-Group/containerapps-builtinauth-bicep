#!/bin/bash
set -euo pipefail

SCRIPT_NAME="postprovision.sh"
LOG_DIR="${PWD}/.azure/logs"
mkdir -p "${LOG_DIR}"
TS="$(date -u +"%Y%m%dT%H%M%SZ")"
LOG_FILE="${LOG_DIR}/postprovision-cosmos-migration-${TS}.log"
LATEST_LOG="${LOG_DIR}/postprovision-cosmos-migration-latest.log"
touch "${LOG_FILE}"
ln -sf "$(basename "${LOG_FILE}")" "${LATEST_LOG}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "[${SCRIPT_NAME}] Starting postprovision hook"
echo "[${SCRIPT_NAME}] Log file: ${LOG_FILE}"
echo "[${SCRIPT_NAME}] Latest log symlink: ${LATEST_LOG}"

get_azd_value() {
  azd env get-value "$1"
}

get_azd_value_optional() {
  azd env get-value "$1" 2>/dev/null || true
}

# Get the required values from azd environment
AZURE_ENV_NAME=$(get_azd_value AZURE_ENV_NAME)
CONTAINER_APP_NAME=$(get_azd_value SERVICE_ACA_NAME)
CLIENT_ID=$(get_azd_value ENTRA_CLIENT_ID)
AZURE_STORAGE_ACCOUNT_NAME=$(get_azd_value_optional AZURE_STORAGE_ACCOUNT_NAME)
AZURE_STORAGE_CONTAINER_NAME=$(get_azd_value_optional AZURE_STORAGE_CONTAINER_NAME)
COSMOS_ACCOUNT_ENDPOINT=$(get_azd_value_optional COSMOS_ACCOUNT_ENDPOINT)
COSMOS_DATABASE_NAME=$(get_azd_value_optional COSMOS_DATABASE_NAME)
COSMOS_METADATA_CONTAINER_NAME=$(get_azd_value_optional COSMOS_METADATA_CONTAINER_NAME)
COSMOS_BATCH_REFERENCE_CONTAINER_NAME=$(get_azd_value_optional COSMOS_BATCH_REFERENCE_CONTAINER_NAME)
AUTO_RUN_COSMOS_BACKFILL=$(get_azd_value_optional AUTO_RUN_COSMOS_BACKFILL)
AUTO_RUN_COSMOS_BACKFILL=${AUTO_RUN_COSMOS_BACKFILL:-true}

# Construct resource group name following the pattern from main.bicep
RESOURCE_GROUP="RG-${AZURE_ENV_NAME}"

if [ -z "$AZURE_ENV_NAME" ] || [ -z "$CONTAINER_APP_NAME" ] || [ -z "$CLIENT_ID" ]; then
  echo "Error: Missing required environment variables"
  echo "AZURE_ENV_NAME: $AZURE_ENV_NAME"
  echo "RESOURCE_GROUP: $RESOURCE_GROUP"
  echo "CONTAINER_APP_NAME: $CONTAINER_APP_NAME"
  echo "CLIENT_ID: $CLIENT_ID"
  exit 1
fi

echo "[${SCRIPT_NAME}] Updating Container App with Entra Client ID..."
echo "[${SCRIPT_NAME}] Resource Group: $RESOURCE_GROUP"
echo "[${SCRIPT_NAME}] Container App: $CONTAINER_APP_NAME"

az containerapp update \
  --name "$CONTAINER_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --set-env-vars "ENTRA_CLIENT_ID=$CLIENT_ID"

echo "[${SCRIPT_NAME}] Container App updated successfully"

if [ "${AUTO_RUN_COSMOS_BACKFILL}" != "true" ]; then
  echo "[${SCRIPT_NAME}] Skipping automatic Cosmos backfill (AUTO_RUN_COSMOS_BACKFILL=${AUTO_RUN_COSMOS_BACKFILL})"
  exit 0
fi

if [ -z "${AZURE_STORAGE_ACCOUNT_NAME}" ] || [ -z "${COSMOS_ACCOUNT_ENDPOINT}" ]; then
  echo "[${SCRIPT_NAME}] Skipping automatic Cosmos backfill due to missing required env values"
  echo "[${SCRIPT_NAME}] AZURE_STORAGE_ACCOUNT_NAME=${AZURE_STORAGE_ACCOUNT_NAME}"
  echo "[${SCRIPT_NAME}] COSMOS_ACCOUNT_ENDPOINT=${COSMOS_ACCOUNT_ENDPOINT}"
  exit 0
fi

# Pick python interpreter (prefer repo venv)
PYTHON_BIN="python3"
if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
fi

echo "[${SCRIPT_NAME}] Running automatic Blob->Cosmos metadata migration"
echo "[${SCRIPT_NAME}] Python: ${PYTHON_BIN}"
echo "[${SCRIPT_NAME}] AZURE_STORAGE_ACCOUNT_NAME=${AZURE_STORAGE_ACCOUNT_NAME}"
echo "[${SCRIPT_NAME}] AZURE_STORAGE_CONTAINER_NAME=${AZURE_STORAGE_CONTAINER_NAME:-tender-documents}"
echo "[${SCRIPT_NAME}] COSMOS_ACCOUNT_ENDPOINT=${COSMOS_ACCOUNT_ENDPOINT}"
echo "[${SCRIPT_NAME}] COSMOS_DATABASE_NAME=${COSMOS_DATABASE_NAME:-kapitol-tender-automation}"
echo "[${SCRIPT_NAME}] COSMOS_METADATA_CONTAINER_NAME=${COSMOS_METADATA_CONTAINER_NAME:-metadata}"
echo "[${SCRIPT_NAME}] COSMOS_BATCH_REFERENCE_CONTAINER_NAME=${COSMOS_BATCH_REFERENCE_CONTAINER_NAME:-batch-reference-index}"

export AZURE_STORAGE_ACCOUNT_NAME
export AZURE_STORAGE_CONTAINER_NAME="${AZURE_STORAGE_CONTAINER_NAME:-tender-documents}"
export COSMOS_ACCOUNT_ENDPOINT
export COSMOS_DATABASE_NAME="${COSMOS_DATABASE_NAME:-kapitol-tender-automation}"
export COSMOS_METADATA_CONTAINER_NAME="${COSMOS_METADATA_CONTAINER_NAME:-metadata}"
export COSMOS_BATCH_REFERENCE_CONTAINER_NAME="${COSMOS_BATCH_REFERENCE_CONTAINER_NAME:-batch-reference-index}"

if ! "${PYTHON_BIN}" -c "import azure.cosmos" >/dev/null 2>&1; then
  echo "[${SCRIPT_NAME}] ERROR: python environment is missing azure.cosmos"
  echo "[${SCRIPT_NAME}] Install deps with: ${PYTHON_BIN} -m pip install -r backend/requirements.txt"
  exit 1
fi

run_step() {
  echo "[${SCRIPT_NAME}] RUN: $*"
  "$@"
  echo "[${SCRIPT_NAME}] OK: $*"
}

run_step "${PYTHON_BIN}" backend/scripts/backfill_metadata_to_cosmos.py --dry-run
run_step "${PYTHON_BIN}" backend/scripts/backfill_metadata_to_cosmos.py
run_step "${PYTHON_BIN}" backend/scripts/validate_cosmos_backfill.py --sample-size 25 --max-mismatches 0

echo "[${SCRIPT_NAME}] Automatic Cosmos metadata migration completed successfully"
