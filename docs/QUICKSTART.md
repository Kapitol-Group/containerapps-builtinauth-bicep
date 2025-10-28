# Developer Quick Start Guide

## Overview
This guide will help you set up your local development environment for the Construction Tender Automation system.

## Prerequisites

- Python 3.12+
- Node.js 20+
- Git
- VS Code (recommended)

## Initial Setup

### 1. Clone and Navigate
```bash
git clone <repository-url>
cd KapitolTenderAutomation
```

### 2. Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (optional for local development)
cat > .env << EOF
AZURE_STORAGE_ACCOUNT_NAME=devstorageaccount001
UIPATH_API_URL=http://localhost:8080
UIPATH_API_KEY=dev-key
FRONTEND_URL=http://localhost:3000
EOF
```

### 3. Frontend Setup

```bash
# Open new terminal
cd frontend

# Install dependencies
npm install
```

## Running Locally

### Terminal 1: Backend (Flask)

```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
python app.py
```

Backend will run on `http://localhost:8080`

### Terminal 2: Frontend (React)

```bash
cd frontend
npm start
```

Frontend will run on `http://localhost:3000`

## Development Workflow

### Making Changes

1. **Backend Changes**:
   - Edit files in `backend/`
   - Flask auto-reloads in debug mode
   - Test endpoints with curl or Postman
   
2. **Frontend Changes**:
   - Edit files in `frontend/src/`
   - React hot-reloads automatically
   - Changes appear immediately in browser

### Testing API Endpoints

```bash
# Health check
curl http://localhost:8080/api/health

# List tenders
curl http://localhost:8080/api/tenders

# Create tender
curl -X POST http://localhost:8080/api/tenders \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Tender", "sharepoint_path": "/path/to/folder"}'
```

### Code Structure

**Backend**:
```
backend/
├── app.py              # Main Flask application
├── services/           # Business logic
│   ├── blob_storage.py
│   └── uipath_client.py
└── utils/              # Helper functions
    └── auth.py
```

**Frontend**:
```
frontend/src/
├── components/         # Reusable React components
├── pages/             # Page components
├── services/          # API clients
├── types/             # TypeScript types
└── App.tsx            # Main app component
```

## Common Tasks

### Add New API Endpoint

1. Add route in `backend/app.py`:
```python
@app.get('/api/my-endpoint')
def my_endpoint():
    return jsonify({'data': 'response'})
```

2. Add to API client in `frontend/src/services/api.ts`:
```typescript
export const myApi = {
  getData: async (): Promise<MyData> => {
    const response = await api.get('/my-endpoint');
    return response.data;
  }
};
```

### Add New React Component

```bash
cd frontend/src/components
# Create MyComponent.tsx and MyComponent.css
```

```typescript
// MyComponent.tsx
import React from 'react';
import './MyComponent.css';

interface MyComponentProps {
  title: string;
}

const MyComponent: React.FC<MyComponentProps> = ({ title }) => {
  return <div className="my-component">{title}</div>;
};

export default MyComponent;
```

## Debugging

### Backend Debugging (VS Code)

Create `.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Flask",
      "type": "python",
      "request": "launch",
      "module": "flask",
      "env": {
        "FLASK_APP": "app.py",
        "FLASK_DEBUG": "1"
      },
      "args": ["run", "--port", "8080"],
      "jinja": true,
      "cwd": "${workspaceFolder}/backend"
    }
  ]
}
```

### Frontend Debugging

- Use Chrome DevTools
- React DevTools extension recommended
- Network tab for API debugging

## Tips & Tricks

1. **Mock Data**: Backend services return mock data when Azure credentials aren't configured
2. **CORS**: Frontend proxy in `package.json` routes `/api` to backend
3. **Type Safety**: Run `npm run type-check` in frontend to check TypeScript errors
4. **Linting**: Run `npm run lint` for code quality checks

## Troubleshooting

### Backend won't start
- Check Python version: `python --version`
- Verify virtual environment is activated
- Install missing dependencies: `pip install -r requirements.txt`

### Frontend won't compile
- Delete `node_modules` and run `npm install`
- Clear npm cache: `npm cache clean --force`
- Check Node version: `node --version`

### API calls fail with CORS errors
- Ensure backend is running on port 8080
- Check `package.json` proxy configuration
- Verify backend CORS settings

## Next Steps

- Read `PROJECT_STATUS.md` for implementation details
- Check `DEPLOYMENT.md` for Azure deployment
- Review `tender-automation-plan.md` for full requirements

## Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [React Documentation](https://react.dev/)
- [Azure Container Apps](https://learn.microsoft.com/azure/container-apps/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
