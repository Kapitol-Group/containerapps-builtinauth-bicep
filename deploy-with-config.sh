#!/bin/bash

echo "🚀 Deploying with runtime configuration approach..."
echo ""

# Deploy
echo "📦 Running azd deploy..."
azd deploy

echo ""
echo "✅ Deployment complete!"
echo ""

# Get the update command
echo "🔧 Getting update command..."
UPDATE_CMD=$(azd env get-values | grep "UPDATE_ENTRA_CLIENT_ID_COMMAND" | cut -d'=' -f2- | tr -d '"')

if [ -n "$UPDATE_CMD" ]; then
    echo "📝 Updating container app with ENTRA_CLIENT_ID..."
    echo "Running: $UPDATE_CMD"
    eval $UPDATE_CMD
    
    echo ""
    echo "✅ Container app updated with ENTRA_CLIENT_ID!"
else
    echo "⚠️  Could not find UPDATE_ENTRA_CLIENT_ID_COMMAND. Run manually:"
    echo "    azd env get-values | grep UPDATE_ENTRA_CLIENT_ID_COMMAND"
fi

echo ""
echo "🎉 Setup complete! SharePoint FilePicker should now work."
echo ""
echo "📋 Configuration values:"
azd env get-values | grep -E "ENTRA_CLIENT_ID|ENTRA_TENANT_ID|SHAREPOINT_BASE_URL|SERVICE_ACA_URI"
