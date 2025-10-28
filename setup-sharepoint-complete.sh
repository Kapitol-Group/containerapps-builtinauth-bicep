#!/bin/bash

# SharePoint FilePicker Complete Setup Script
# This script automates the complete setup process for SharePoint FilePicker integration

set -e  # Exit on error

echo "🚀 SharePoint FilePicker Setup Script"
echo "======================================"
echo ""

# Step 1: Install dependencies
echo "📦 Step 1: Installing npm dependencies..."
cd frontend
npm install @azure/msal-react @azure/msal-browser uuid
npm install --save-dev @types/uuid
cd ..
echo "✅ Dependencies installed"
echo ""

# Step 2: First deployment
echo "🏗️  Step 2: First deployment (creating infrastructure)..."
read -p "Press Enter to start first deployment (azd up)..."
azd up

echo ""
echo "✅ First deployment complete!"
echo ""

# Step 3: Get outputs and configure environment
echo "🔑 Step 3: Configuring build-time environment variables..."
echo ""
echo "Getting deployment outputs..."
azd env get-values | grep -E "ENTRA_CLIENT_ID|ENTRA_TENANT_ID"

echo ""
echo "Please provide the following values:"
echo ""

# Get ENTRA_CLIENT_ID
ENTRA_CLIENT_ID=$(azd env get-values | grep "ENTRA_CLIENT_ID" | cut -d'=' -f2 | tr -d '"' | xargs)
if [ -z "$ENTRA_CLIENT_ID" ]; then
    read -p "Enter ENTRA_CLIENT_ID: " ENTRA_CLIENT_ID
else
    echo "Found ENTRA_CLIENT_ID: $ENTRA_CLIENT_ID"
    read -p "Use this value? (Y/n): " use_client_id
    if [[ $use_client_id == "n" || $use_client_id == "N" ]]; then
        read -p "Enter ENTRA_CLIENT_ID: " ENTRA_CLIENT_ID
    fi
fi

# Get ENTRA_TENANT_ID
ENTRA_TENANT_ID=$(azd env get-values | grep "ENTRA_TENANT_ID" | cut -d'=' -f2 | tr -d '"' | xargs)
if [ -z "$ENTRA_TENANT_ID" ]; then
    read -p "Enter ENTRA_TENANT_ID: " ENTRA_TENANT_ID
else
    echo "Found ENTRA_TENANT_ID: $ENTRA_TENANT_ID"
    read -p "Use this value? (Y/n): " use_tenant_id
    if [[ $use_tenant_id == "n" || $use_tenant_id == "N" ]]; then
        read -p "Enter ENTRA_TENANT_ID: " ENTRA_TENANT_ID
    fi
fi

# Get SharePoint URL
read -p "Enter your SharePoint base URL (e.g., https://contoso.sharepoint.com): " SHAREPOINT_URL

# Set environment variables
echo ""
echo "Setting build-time environment variables..."
azd env set VITE_ENTRA_CLIENT_ID "$ENTRA_CLIENT_ID"
azd env set VITE_ENTRA_TENANT_ID "$ENTRA_TENANT_ID"
azd env set VITE_SHAREPOINT_BASE_URL "$SHAREPOINT_URL"

echo "✅ Environment variables configured"
echo ""

# Step 4: Second deployment
echo "🔄 Step 4: Second deployment (rebuilding with SharePoint config)..."
read -p "Press Enter to start second deployment (azd deploy)..."
azd deploy

echo ""
echo "✅ Second deployment complete!"
echo ""

# Step 5: Summary
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "SharePoint FilePicker is now configured with:"
echo "  - Client ID: $ENTRA_CLIENT_ID"
echo "  - Tenant ID: $ENTRA_TENANT_ID"
echo "  - SharePoint URL: $SHAREPOINT_URL"
echo ""
echo "📋 Next Steps:"
echo "1. Visit your app URL (check 'azd env get-values' for SERVICE_ACA_URI)"
echo "2. Grant admin consent for SharePoint permissions in Azure Portal"
echo "3. Test the SharePoint FilePicker in Create New Tender modal"
echo ""
echo "📖 Documentation:"
echo "  - QUICKSTART_SHAREPOINT.md - Quick reference"
echo "  - CONTAINER_APP_ENV_VARS.md - Environment variables guide"
echo "  - SHAREPOINT_IMPLEMENTATION_SUMMARY.md - Complete implementation details"
echo ""
