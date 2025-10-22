---
title: Construction Tender Document Automation Frontend
version: 1.0
date_created: 2025-10-20
last_updated: 2025-10-20
---

# Implementation Plan: Construction Tender Document Automation Frontend

A React-based frontend application for automating construction tender document categorization and metadata extraction, integrated with SharePoint, Azure Blob Storage, and UiPath processing services. This extends the existing Azure Container Apps infrastructure to support a dual-service architecture with Flask backend for secure API operations.

## Architecture and design

### High-Level Architecture
- **Frontend**: React SPA served from Azure Container Apps with Entra ID authentication
- **Backend**: Enhanced Flask API for UiPath integration, file management, and business logic
- **Storage**: Azure Blob Storage with folder support for tender document organization
- **Authentication**: Existing Entra ID setup maintained across both services
- **External Integration**: SharePoint FilePicker for tender selection and UiPath REST API for drawing processing

### Service Architecture
```
[React Frontend] ←→ [Flask Backend API] ←→ [UiPath REST API]
       ↓                    ↓
[Azure Blob Storage] ←→ [SharePoint]
       ↓
[Container Apps Environment with Entra ID]
```

### Data Flow
1. **Tender Creation**: SharePoint FilePicker → React → Flask → Azure Blob Storage
2. **File Management**: Drag/Drop → React → Flask → Blob Storage → Preview System
3. **Metadata Extraction**: File Selection → React → Flask → UiPath API (with title block coordinates)

### Authentication Strategy
- Maintain current Container Apps built-in authentication
- Both React and Flask services use same Entra ID configuration
- Flask backend handles sensitive UiPath API credentials
- Frontend receives user context via `X-MS-CLIENT-PRINCIPAL` header

## Tasks

### Phase 1: Infrastructure Enhancement
- [ ] **Modify Bicep templates for dual-service architecture**
  - Update `main.bicep` to support frontend and backend services
  - Create new container app configuration for React frontend
  - Configure shared Container Apps environment
  - Add Azure Blob Storage account with hierarchical namespace (folder support)

- [ ] **Update Azure Developer CLI configuration**
  - Modify `azure.yaml` to include both frontend and backend services
  - Configure separate Docker builds for React and Flask
  - Set up service-specific environment variables

### Phase 2: Backend API Development
- [ ] **Enhance Flask application with REST API endpoints**
  - `/api/tenders` - CRUD operations for tender management
  - `/api/files` - File upload, categorization, and metadata endpoints
  - `/api/uipath` - UiPath integration for drawing processing
  - `/api/sharepoint` - SharePoint integration helpers

- [ ] **Implement file management system**
  - Azure Blob Storage client integration
  - File upload/download with progress tracking  
  - File type validation and preview generation
  - Folder structure management for tender organization

- [ ] **UiPath integration layer**
  - REST API client for UiPath communication
  - Title block coordinate processing (pixel format)
  - Job submission and status tracking framework
  - Error handling and retry logic

- [ ] **Authentication and security enhancements**
  - Extract user context from Container Apps headers
  - Implement role-based access control
  - Secure UiPath API credential management
  - CORS configuration for React frontend

### Phase 3: React Frontend Development
- [ ] **Project setup and build configuration**
  - Create React application with TypeScript
  - Configure Dockerfile for production builds
  - Set up Azure Container Apps deployment pipeline
  - Integrate with existing Entra ID authentication

- [ ] **Landing page and navigation**
  - Previous tenders listing with search/filter
  - Tender creation modal with SharePoint FilePicker integration
  - User authentication state management
  - Navigation and routing setup

- [ ] **Tender management interface**
  - File drag-and-drop area with progress indicators
  - Left panel file browser with categorization
  - Right panel preview system (PDF, Office docs)
  - File selection and batch operations

- [ ] **Drawing processing workflow**
  - "Queue Extraction" modal with discipline selection
  - Drawing title block region selection tool
  - Rectangle drawing interface with pixel coordinate capture
  - Integration with backend UiPath API calls

### Phase 4: SharePoint Integration
- [ ] **FilePicker implementation**
  - SharePoint `_layouts/15/FilePicker.aspx` integration
  - Tender folder selection and validation
  - Output location configuration
  - SharePoint authentication flow

### Phase 5: File Preview System
- [ ] **PDF preview implementation**
  - PDF.js integration for in-browser viewing
  - Thumbnail generation for file listings
  - Zoom and navigation controls
  - Page-level metadata display

- [ ] **Office document preview**
  - Microsoft Office Online integration
  - Document viewer embedding
  - Read-only preview for supported formats
  - Fallback download option for unsupported types

### Phase 6: Testing and Deployment
- [ ] **Unit and integration testing**
  - Flask API endpoint testing
  - React component testing with Jest/RTL
  - UiPath integration testing (mocked and real)
  - File upload/download functionality testing

- [ ] **End-to-end testing**
  - Complete tender workflow testing
  - SharePoint integration testing
  - Drawing processing workflow
  - Multi-user authentication scenarios

- [ ] **Production deployment**
  - Azure Container Apps deployment validation
  - Environment-specific configuration
  - Performance testing and optimization
  - Monitoring and logging setup

## Open questions

1. **SharePoint FilePicker Integration Approach**: How should the `_layouts/15/FilePicker.aspx` component be embedded in the React application? Should it be iframe-based, popup window, or is there a modern alternative that provides better UX while maintaining the same functionality? -> As per https://learn.microsoft.com/en-us/onedrive/developer/controls/file-pickers/?view=odsp-graph-online

2. **Drawing Title Block Selection UX**: For the rectangle drawing interface on drawings, what level of precision is required? Should we implement zoom functionality, guide overlays, or snap-to-grid features to help users accurately select title block regions? ->Not for now

3. **File Processing Scalability**: Given that UiPath processing is fire-and-forget initially, how should we handle scenarios where users upload large batches of drawings? Should we implement queue management, batch size limits, or progress tracking even without real-time status updates? -> Not for now