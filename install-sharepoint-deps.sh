#!/bin/bash

# SharePoint FilePicker Dependencies Installation Script

echo "🔧 Installing SharePoint FilePicker dependencies..."

cd frontend

echo "📦 Installing @azure/msal-react @azure/msal-browser uuid..."
npm install @azure/msal-react @azure/msal-browser uuid

echo "📦 Installing TypeScript types..."
npm install --save-dev @types/uuid

echo "✅ Dependencies installed successfully!"
echo ""
echo "📝 Next steps:"
echo "1. Configure environment variables in frontend/.env.local:"
echo "   VITE_ENTRA_CLIENT_ID=<your-client-id>"
echo "   VITE_ENTRA_TENANT_ID=<your-tenant-id>"
echo "   VITE_SHAREPOINT_BASE_URL=https://yourtenant.sharepoint.com"
echo ""
echo "2. Update Entra ID app registration with SharePoint permissions"
echo "3. Test the SharePoint FilePicker in CreateTenderModal"
echo ""
echo "See SHAREPOINT_FILEPICKER_IMPLEMENTATION.md for detailed instructions."
