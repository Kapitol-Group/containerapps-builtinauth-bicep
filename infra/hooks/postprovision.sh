#!/bin/bash
set -e

echo "Running postprovision hook..."

# Get the required values from azd environment
AZURE_ENV_NAME=$(azd env get-value AZURE_ENV_NAME)
CONTAINER_APP_NAME=$(azd env get-value SERVICE_ACA_NAME)
CLIENT_ID=$(azd env get-value ENTRA_CLIENT_ID)

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

echo "Updating Container App with Entra Client ID..."
echo "Resource Group: $RESOURCE_GROUP"
echo "Container App: $CONTAINER_APP_NAME"

az containerapp update \
  --name "$CONTAINER_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --set-env-vars "ENTRA_CLIENT_ID=$CLIENT_ID"

echo "Container App updated successfully!"
