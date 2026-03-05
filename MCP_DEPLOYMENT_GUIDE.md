# AgentStudio MCP Ecosystem - Architecture & Deployment Guide

## Table of Contents
1. [System Architecture](#1-system-architecture)
2. [Component Overview](#2-component-overview)
3. [Azure Infrastructure](#3-azure-infrastructure)
4. [CI/CD Pipeline](#4-cicd-pipeline)
5. [Deployment Procedures](#5-deployment-procedures)
6. [Dynamic MCP Server](#6-dynamic-mcp-server)
7. [Post-Deployment Verification](#7-post-deployment-verification)

---

## 1. System Architecture

### High-Level Architecture Diagram

```
                                    ┌─────────────────────────────────────────────────────────────┐
                                    │                    AZURE CLOUD (UAE North)                   │
                                    │                                                              │
┌──────────────┐                    │  ┌─────────────────────────────────────────────────────┐   │
│   Internet   │                    │  │              Azure Front Door (CDN + WAF)            │   │
│    Users     │────HTTPS───────────┼──│         agentstudio365.com (Custom Domain)          │   │
└──────────────┘                    │  │                   + SSL/TLS Termination              │   │
                                    │  └───────────────────────┬─────────────────────────────┘   │
                                    │                          │                                  │
                                    │            ┌─────────────┴─────────────┐                   │
                                    │            │                           │                   │
                                    │            ▼                           ▼                   │
                                    │  ┌─────────────────────┐    ┌─────────────────────┐       │
                                    │  │  Container App:     │    │  Container App:     │       │
                                    │  │  agentstudio-frontend│   │  agentstudio-backend│       │
                                    │  │  (Nginx + React)    │    │  (FastAPI + Python) │       │
                                    │  │  Port: 80           │    │  Port: 8000         │       │
                                    │  └─────────────────────┘    └──────────┬──────────┘       │
                                    │                                        │                   │
                                    │                          ┌─────────────┼─────────────┐    │
                                    │                          │             │             │    │
                                    │                          ▼             ▼             ▼    │
                                    │               ┌──────────────┐ ┌─────────────┐ ┌────────┐│
                                    │               │ PostgreSQL   │ │    Redis    │ │  ACR   ││
                                    │               │ Flexible     │ │   Cache     │ │        ││
                                    │               │ Server       │ │             │ │        ││
                                    │               └──────────────┘ └─────────────┘ └────────┘│
                                    │                                                          │
                                    │  ┌─────────────────────┐                                 │
                                    │  │  Container App:     │  (Optional - Future)            │
                                    │  │  agentstudio-mcp    │                                 │
                                    │  │  (Dynamic MCP Server)│                                │
                                    │  │  Port: 3000         │                                 │
                                    │  └─────────────────────┘                                 │
                                    └──────────────────────────────────────────────────────────┘

                                    ┌─────────────────────────────────────────────────────────────┐
                                    │                      GITHUB (CI/CD)                          │
                                    │                                                              │
                                    │  ┌──────────────────────────────────────────────────────┐   │
                                    │  │  Repository: aidemystagent                            │   │
                                    │  │  Branch: development (main for production)            │   │
                                    │  │                                                        │   │
                                    │  │  ┌──────────────────────────────────────────────────┐│   │
                                    │  │  │  GitHub Actions Workflow: azure-deploy.yml       ││   │
                                    │  │  │  Triggers: push to main/development              ││   │
                                    │  │  │                                                    ││   │
                                    │  │  │  Jobs:                                            ││   │
                                    │  │  │  1. build-backend  → Push to ACR                 ││   │
                                    │  │  │  2. build-frontend → Push to ACR                 ││   │
                                    │  │  │  3. deploy         → Update Container Apps       ││   │
                                    │  │  │  4. notify         → Status notification         ││   │
                                    │  │  └──────────────────────────────────────────────────┘│   │
                                    │  └──────────────────────────────────────────────────────┘   │
                                    └─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
1. User Request Flow:
   User → Azure Front Door → Container App (Frontend or Backend) → Database/Redis

2. Agent Execution Flow:
   Frontend → Backend API → LangGraph Engine → Tool Execution → RAG/External APIs → Response

3. MCP Tool Execution Flow (Future):
   Agent → Dynamic MCP Server → AgentStudio API (credentials) → External API → Response
```

---

## 2. Component Overview

### 2.1 Frontend (React + TypeScript)

| Property | Value |
|----------|-------|
| Framework | React 18 + TypeScript + Vite |
| UI Library | Ant Design 5.0 |
| State Management | Zustand + TanStack Query |
| Build Output | Static files served by Nginx |
| Container Port | 80 |
| Health Endpoint | `/health` |

**Dockerfile Strategy**: Multi-stage build
1. Stage 1: Node.js builder - installs deps, builds React app
2. Stage 2: Nginx Alpine - serves static files

### 2.2 Backend (FastAPI + Python)

| Property | Value |
|----------|-------|
| Framework | FastAPI 0.104 + Python 3.11 |
| ORM | SQLAlchemy 2.0 (async) |
| Agent Engine | LangGraph 0.2+ |
| Container Port | 8000 |
| Health Endpoint | `/health` |
| Workers | 4 (uvicorn) |

**Dockerfile Strategy**: Multi-stage build
1. Stage 1: Python builder - installs dependencies
2. Stage 2: Python slim + Node.js - runs application

**Startup Script** (`start.sh`):
```bash
#!/bin/bash
set -e
alembic upgrade head          # Run migrations
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 2.3 Dynamic MCP Server (FastMCP + Python)

| Property | Value |
|----------|-------|
| Framework | FastMCP + Python 3.11 |
| Transport | SSE (Server-Sent Events) |
| Container Port | 3000 |
| Health Endpoint | `/health` |

**Key Features**:
- Dynamically loads tool definitions from AgentStudio API
- Executes API calls on behalf of agents
- Manages credentials securely (LLM never sees secrets)
- Periodic tool refresh (configurable interval)

---

## 3. Azure Infrastructure

### 3.1 Resource Inventory

| Resource Type | Name | Purpose |
|---------------|------|---------|
| Resource Group | `agentstudio-rg` | Contains all resources |
| Container Registry | `agentstudioacr` | Docker image storage |
| Container App | `agentstudio-backend` | FastAPI backend |
| Container App | `agentstudio-frontend` | React/Nginx frontend |
| Container App | `agentstudio-mcp` | Dynamic MCP Server (future) |
| PostgreSQL | `agentstudio-db` | Database (Flexible Server) |
| Redis Cache | `agentstudio-redis` | Caching + Sessions |
| Front Door | `agentstudio-fd` | CDN + SSL + WAF |
| Key Vault | `agentstudio-kv` | Secrets management |

### 3.2 Azure Front Door Configuration

**Domain**: `agentstudio365.com`

**Routing Rules**:
| Route | Origin | Path Pattern |
|-------|--------|--------------|
| Frontend | agentstudio-frontend | `/*` |
| Backend API | agentstudio-backend | `/api/*` |

**Features**:
- SSL/TLS termination with managed certificate
- WAF (Web Application Firewall) for security
- Global load balancing
- Caching for static assets
- Health probes for backend services

### 3.3 Container Apps Environment

**Environment Name**: `agentstudio-env`

**Configuration**:
- Auto-scaling: 1-10 replicas based on HTTP traffic
- vCPU: 0.5-2 per container
- Memory: 1Gi-4Gi per container
- Ingress: External (via Front Door)

### 3.4 Environment Variables

**Backend Container**:
```
SECRET_KEY=<from-key-vault>
DATABASE_URL=postgresql+asyncpg://<user>:<pass>@agentstudio-db.postgres.database.azure.com:5432/agentstudio
REDIS_URL=redis://:<access-key>@agentstudio-redis.redis.cache.windows.net:6380?ssl=true
OPENAI_API_KEY=<from-key-vault>
ANTHROPIC_API_KEY=<from-key-vault>
MCP_INTERNAL_API_KEY=<from-key-vault>
```

**Frontend Container**:
```
VITE_API_BASE_URL=https://agentstudio365.com
```

**Dynamic MCP Server** (future):
```
AGENTSTUDIO_API_URL=https://agentstudio365.com
MCP_INTERNAL_API_KEY=<from-key-vault>
REDIS_URL=<same-as-backend>
```

---

## 4. CI/CD Pipeline

### 4.1 GitHub Actions Workflow

**File**: `.github/workflows/azure-deploy.yml`

**Triggers**:
- Push to `main` branch → Production deployment
- Push to `development` branch → Staging deployment
- Manual dispatch with environment selection

### 4.2 Workflow Jobs

```yaml
Jobs Flow:
┌─────────────────┐     ┌──────────────────┐
│  build-backend  │     │  build-frontend  │
│  (parallel)     │     │  (parallel)      │
└────────┬────────┘     └────────┬─────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
            ┌────────────────┐
            │     deploy     │
            │ (after builds) │
            └────────┬───────┘
                     │
                     ▼
            ┌────────────────┐
            │     notify     │
            │   (always)     │
            └────────────────┘
```

### 4.3 Job Details

**Job 1: build-backend**
```yaml
Steps:
1. Checkout code
2. Set up Docker Buildx
3. Log in to Azure Container Registry
4. Extract metadata (tags: sha, branch, latest)
5. Build and push image to ACR
```

**Job 2: build-frontend**
```yaml
Steps:
1. Checkout code
2. Set up Docker Buildx
3. Log in to Azure Container Registry
4. Extract metadata (tags: sha, branch, latest)
5. Build and push image with VITE_API_BASE_URL build arg
```

**Job 3: deploy**
```yaml
Steps:
1. Azure Login (service principal)
2. Update Backend Container App with new image
3. Update Frontend Container App with new image
4. Health check Backend (curl /health)
5. Health check Frontend (curl /health)
```

**Job 4: notify**
```yaml
Steps:
1. Check deployment status
2. Output success/failure message with URLs
```

### 4.4 Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `AZURE_CREDENTIALS` | Service principal JSON for Azure login |
| `ACR_LOGIN_SERVER` | `agentstudioacr.azurecr.io` |
| `ACR_USERNAME` | ACR admin username |
| `ACR_PASSWORD` | ACR admin password |
| `SECRET_KEY` | Application secret key |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `API_BASE_URL` | `https://agentstudio365.com` |

---

## 5. Deployment Procedures

### 5.1 Automatic Deployment (Recommended)

**Trigger**: Push to `development` branch

```bash
# Your changes are already pushed. The workflow should trigger automatically.
# Check status at: https://github.com/<org>/aidemystagent/actions
```

### 5.2 Manual Workflow Dispatch

1. Go to GitHub repository → Actions tab
2. Select "Deploy to Azure" workflow
3. Click "Run workflow"
4. Select branch: `development` or `main`
5. Select environment: `staging` or `production`
6. Click "Run workflow"

### 5.3 Direct Azure CLI Deployment

```bash
# 1. Login to Azure
az login

# 2. Login to ACR
az acr login --name agentstudioacr

# 3. Build and push Backend
cd backend
az acr build --registry agentstudioacr --image agentstudio-backend:latest .

# 4. Build and push Frontend
cd ../frontend
az acr build --registry agentstudioacr --image agentstudio-frontend:latest \
  --build-arg VITE_API_BASE_URL=https://agentstudio365.com .

# 5. Update Backend Container App
az containerapp update \
  --name agentstudio-backend \
  --resource-group agentstudio-rg \
  --image agentstudioacr.azurecr.io/agentstudio-backend:latest

# 6. Update Frontend Container App
az containerapp update \
  --name agentstudio-frontend \
  --resource-group agentstudio-rg \
  --image agentstudioacr.azurecr.io/agentstudio-frontend:latest

# 7. Check deployment status
az containerapp show --name agentstudio-backend --resource-group agentstudio-rg \
  --query "properties.runningStatus"
az containerapp show --name agentstudio-frontend --resource-group agentstudio-rg \
  --query "properties.runningStatus"
```

### 5.4 Database Migrations

Migrations run automatically via `start.sh` on container startup:

```bash
alembic upgrade head
```

**New migrations in this release**:
- `009_add_mcp_servers_table.py` - Creates `mcp_servers` table
- `010_add_dynamic_mcp_tools_table.py` - Creates `dynamic_mcp_tools` table

---

## 6. Dynamic MCP Server

### 6.1 Architecture

```
┌────────────────────┐     ┌─────────────────────────┐     ┌──────────────────┐
│    AI Agent        │────▶│  Dynamic MCP Server     │────▶│  External APIs   │
│  (LangGraph)       │     │  (FastMCP)              │     │  (Weather, etc.) │
└────────────────────┘     └────────────┬────────────┘     └──────────────────┘
                                        │
                                        ▼
                           ┌─────────────────────────┐
                           │  AgentStudio Backend    │
                           │  - Tool definitions     │
                           │  - Credentials (secure) │
                           └─────────────────────────┘
```

### 6.2 Files Structure

```
mcp-servers/
├── dynamic-server/
│   ├── server.py           # Main FastMCP server
│   ├── config.py           # Pydantic settings
│   ├── Dockerfile          # Container definition
│   ├── requirements.txt    # Python dependencies
│   └── .env.example        # Environment template
└── docker-compose.yml      # Local development
```

### 6.3 Deployment Commands

```bash
# Build and push MCP server image
cd mcp-servers/dynamic-server
az acr build --registry agentstudioacr --image dynamic-mcp-server:latest .

# Create new Container App for MCP Server
az containerapp create \
  --name agentstudio-mcp \
  --resource-group agentstudio-rg \
  --environment agentstudio-env \
  --image agentstudioacr.azurecr.io/dynamic-mcp-server:latest \
  --target-port 3000 \
  --ingress internal \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 0.5 \
  --memory 1Gi \
  --env-vars \
    "AGENTSTUDIO_API_URL=https://agentstudio365.com" \
    "MCP_INTERNAL_API_KEY=secretref:mcp-internal-key" \
    "REDIS_URL=secretref:redis-url"
```

### 6.4 Add to GitHub Workflow (Future)

Add new job to `.github/workflows/azure-deploy.yml`:

```yaml
build-mcp-server:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: docker/setup-buildx-action@v3
    - uses: azure/docker-login@v1
      with:
        login-server: ${{ secrets.ACR_LOGIN_SERVER }}
        username: ${{ secrets.ACR_USERNAME }}
        password: ${{ secrets.ACR_PASSWORD }}
    - uses: docker/build-push-action@v5
      with:
        context: ./mcp-servers/dynamic-server
        push: true
        tags: ${{ secrets.ACR_LOGIN_SERVER }}/dynamic-mcp-server:latest
```

---

## 7. Post-Deployment Verification

### 7.1 Health Checks

```bash
# Backend health
curl https://agentstudio365.com/api/v1/health

# Frontend health
curl https://agentstudio365.com/health

# Expected response: {"status": "healthy"} or 200 OK
```

### 7.2 API Endpoint Tests

```bash
# Get auth token first
TOKEN=$(curl -s -X POST https://agentstudio365.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}' \
  | jq -r '.access_token')

# Test MCP Servers endpoint
curl -H "Authorization: Bearer $TOKEN" \
  https://agentstudio365.com/api/v1/mcp-servers

# Test MCP Tools endpoint
curl -H "Authorization: Bearer $TOKEN" \
  https://agentstudio365.com/api/v1/mcp-tools

# Expected: JSON response with empty or populated arrays
```

### 7.3 UI Verification Checklist

1. [ ] Login to https://agentstudio365.com
2. [ ] Verify sidebar shows "MCP Servers" menu item
3. [ ] Verify sidebar shows "MCP Tools" menu item
4. [ ] Navigate to MCP Servers page - loads without errors
5. [ ] Navigate to MCP Tools page - loads without errors
6. [ ] Create a test MCP server registration
7. [ ] Create a test dynamic MCP tool
8. [ ] Verify tool appears in list

### 7.4 Azure Container Logs

```bash
# View backend logs
az containerapp logs show \
  --name agentstudio-backend \
  --resource-group agentstudio-rg \
  --follow

# View frontend logs
az containerapp logs show \
  --name agentstudio-frontend \
  --resource-group agentstudio-rg \
  --follow

# Check for migration success
az containerapp logs show \
  --name agentstudio-backend \
  --resource-group agentstudio-rg \
  | grep -i "migration\|alembic"
```

---

## Summary: Recommended Deployment Steps

### For Current Changes (Backend + Frontend)

1. **Check GitHub Actions**: Go to repository → Actions → verify workflow running
2. **If not running**: Manually trigger workflow for `development` branch
3. **Wait**: ~5-10 minutes for build and deploy
4. **Verify**: Run health checks and UI verification

### For Dynamic MCP Server (Future)

1. Create MCP internal API key in Azure Key Vault
2. Build and push MCP server image to ACR
3. Create new Container App with internal ingress
4. Update LangGraph engine to connect to MCP server
5. Test end-to-end tool execution

---

## Files Modified in This Release

### Backend
- `backend/app/models/mcp_server.py` (new)
- `backend/app/models/dynamic_mcp_tool.py` (new)
- `backend/app/schemas/mcp_server.py` (new)
- `backend/app/schemas/tool.py` (extended)
- `backend/app/api/v1/mcp_servers.py` (new)
- `backend/app/api/v1/mcp_tools.py` (new)
- `backend/app/api/v1/credentials.py` (extended)
- `backend/app/services/mcp_discovery.py` (new)
- `backend/app/main.py` (router registration)
- `backend/alembic/versions/009_*.py` (new migration)
- `backend/alembic/versions/010_*.py` (new migration)

### Frontend
- `frontend/src/pages/MCPServers.tsx` (new)
- `frontend/src/pages/DynamicMCPTools.tsx` (new)
- `frontend/src/components/MCPServers/*` (new)
- `frontend/src/components/MCPTools/*` (new)
- `frontend/src/features/mcp-servers/mcpServerService.ts` (new)
- `frontend/src/features/mcp-tools/mcpToolService.ts` (new)
- `frontend/src/App.tsx` (routes)
- `frontend/src/components/Common/MainLayout.tsx` (navigation)

### MCP Server
- `mcp-servers/dynamic-server/*` (all new)
