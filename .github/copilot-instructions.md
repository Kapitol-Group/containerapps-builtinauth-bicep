# AI Coding Agent Instructions

## Project Overview

This is an **Azure Container Apps + Entra ID Authentication** template that demonstrates secure containerized web applications using built-in authentication. The project combines a Flask web app with Azure's managed identity and federated credentials for seamless authentication without client secrets.

## Architecture Components

### Application Stack
- **Flask app** (`app.py`): Minimal web server with Entra ID header parsing via `X-MS-CLIENT-PRINCIPAL` 
- **Gunicorn**: Production WSGI server (`gunicorn.conf.py`) configured for port 50505
- **Docker**: Multi-stage build with Python 3.12 base

### Infrastructure (Bicep)
- **Main deployment** (`infra/main.bicep`): Subscription-scoped with resource group creation
- **Container Apps** (`infra/aca.bicep`): User-assigned managed identity + container app deployment
- **Core modules** (`infra/core/`): Reusable Bicep components for container registry, environment, monitoring
- **Authentication setup**: Commented out app registration and token store (see `main.bicep` line 71+)

### Key Patterns
- **Managed Identity Flow**: No secrets stored - uses federated identity credentials for Azure auth
- **Built-in Auth**: Container Apps handles authentication; app reads user claims from headers
- **azd Integration**: Uses Azure Developer CLI for streamlined deployment workflow

## Development Workflows

### Local Development
```bash
# Standard Flask development (no auth simulation)
python3 -m pip install -r requirements.txt
python3 -m flask run --port 50505 --debug
```

### Deployment
```bash
# Complete infrastructure + application deployment
azd auth login
azd up  # Provisions all Azure resources and deploys code
azd down  # Cleanup resources
```

### Authentication Testing
- **Local**: No auth headers present - `extract_username()` returns "You" 
- **Azure**: Container Apps injects `X-MS-CLIENT-PRINCIPAL` header with base64-encoded user claims

## Project-Specific Conventions

### Port Configuration
- **Container port**: 50505 (hardcoded in `Dockerfile`, `gunicorn.conf.py`, `aca.bicep`)
- **Development**: Flask defaults to 50505 in local runs
- **Change impact**: Must update all three locations simultaneously

### Bicep Patterns
- **Resource naming**: Uses `${prefix}-${resourceToken}` pattern for uniqueness
- **Conditional deployment**: Uses `exists` parameters for incremental updates (see `aca.bicep`)
- **Managed identity secrets**: Container apps receive identity client ID as secret `override-use-mi-fic-assertion-client-id`

### Authentication Flow
```python
# Extract user from Container Apps built-in auth headers
def extract_username(headers, default_username="You"):
    token = json.loads(base64.b64decode(headers.get("X-MS-CLIENT-PRINCIPAL")))
    claims = {claim["typ"]: claim["val"] for claim in token["claims"]}
    return claims.get("name", default_username)
```

## Key Files for AI Understanding

- **`azure.yaml`**: azd configuration defining service mapping and Docker remote build
- **`infra/main.bicep`**: Complete infrastructure definition with commented auth sections
- **`infra/aca.bicep`**: Container app and managed identity creation patterns
- **`app.py`**: Authentication header parsing and Flask route patterns
- **`gunicorn.conf.py`**: Production server configuration with worker/thread scaling

## Critical Integration Points

### Azure Developer CLI (azd)
- Service name `aca` maps to project root with Python language detection
- Remote Docker builds in Azure Container Registry (not local)
- Infrastructure parameters flow through `infra/main.parameters.json`

### Container Apps Authentication
- Logout URL: `/.auth/logout` (built-in endpoint)
- User claims available in `X-MS-CLIENT-PRINCIPAL` header when deployed
- Token store configuration available but currently disabled (see `includeTokenStore` parameter)

## Debugging Approach

1. **Local issues**: Check Flask logs, verify port 50505 availability
2. **Deployment issues**: Use `azd logs` or Azure Portal Container App → Log stream
3. **Auth issues**: Verify Entra app registration and federated credentials setup
4. **Bicep issues**: Check resource naming conflicts (prefix + resourceToken uniqueness)