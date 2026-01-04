# Azure Deployment & CI/CD Guide

This guide covers deploying AgentStudio to Azure using containerized services with automated CI/CD pipelines.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Azure Components](#azure-components)
3. [Prerequisites](#prerequisites)
4. [Infrastructure Setup](#infrastructure-setup)
5. [CI/CD Pipeline Setup](#cicd-pipeline-setup)
6. [Environment Configuration](#environment-configuration)
7. [Security Best Practices](#security-best-practices)
8. [Monitoring & Logging](#monitoring--logging)
9. [Cost Optimization](#cost-optimization)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Azure Cloud                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                        Azure Front Door / CDN                            │ │
│  │                    (SSL Termination, WAF, Caching)                       │ │
│  └─────────────────────────────────┬───────────────────────────────────────┘ │
│                                    │                                          │
│  ┌─────────────────────────────────┴───────────────────────────────────────┐ │
│  │                     Azure Container Apps Environment                     │ │
│  │  ┌─────────────────────┐     ┌─────────────────────┐                    │ │
│  │  │   Frontend App      │     │   Backend API       │                    │ │
│  │  │   (React/Nginx)     │────▶│   (FastAPI/Python)  │                    │ │
│  │  │   Port: 80          │     │   Port: 8000        │                    │ │
│  │  └─────────────────────┘     └──────────┬──────────┘                    │ │
│  └─────────────────────────────────────────┼───────────────────────────────┘ │
│                                            │                                  │
│  ┌─────────────────────────────────────────┼───────────────────────────────┐ │
│  │                          Data Layer                                      │ │
│  │  ┌─────────────────────┐     ┌─────────────────────┐                    │ │
│  │  │  Azure Database     │     │   Azure Cache       │                    │ │
│  │  │  for PostgreSQL     │     │   for Redis         │                    │ │
│  │  │  (Flexible Server)  │     │   (Premium)         │                    │ │
│  │  └─────────────────────┘     └─────────────────────┘                    │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                        Supporting Services                               │ │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                │ │
│  │  │ Azure Key     │  │ Azure         │  │ Azure         │                │ │
│  │  │ Vault         │  │ Container     │  │ Monitor       │                │ │
│  │  │ (Secrets)     │  │ Registry      │  │ (Logs/Metrics)│                │ │
│  │  └───────────────┘  └───────────────┘  └───────────────┘                │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Azure Components

### Recommended Services

| Component | Azure Service | SKU/Tier | Purpose |
|-----------|--------------|----------|---------|
| **Container Orchestration** | Azure Container Apps | Consumption | Serverless containers with auto-scaling |
| **Container Registry** | Azure Container Registry | Basic/Standard | Store Docker images |
| **Database** | Azure Database for PostgreSQL | Flexible Server (Burstable B1ms) | Primary database |
| **Cache** | Azure Cache for Redis | Basic C0 / Standard C1 | Session & cache storage |
| **Secrets** | Azure Key Vault | Standard | Store API keys, credentials |
| **CDN/WAF** | Azure Front Door | Standard | Global load balancing, WAF, SSL |
| **DNS** | Azure DNS | - | Domain management |
| **Monitoring** | Azure Monitor + Log Analytics | - | Logs, metrics, alerts |
| **CI/CD** | GitHub Actions or Azure DevOps | - | Automated deployments |

### Alternative: Azure Kubernetes Service (AKS)

For larger scale deployments:

| Component | Azure Service | When to Use |
|-----------|--------------|-------------|
| **Orchestration** | Azure Kubernetes Service (AKS) | High traffic, complex scaling needs |
| **Ingress** | NGINX Ingress / Application Gateway | Advanced routing |
| **Service Mesh** | Istio / Linkerd | Microservices communication |

---

## Prerequisites

### 1. Azure CLI Setup

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login to Azure
az login

# Set subscription
az account set --subscription "Your-Subscription-Name"
```

### 2. Required Tools

```bash
# Docker
sudo apt-get install docker.io

# GitHub CLI (for GitHub Actions)
sudo apt-get install gh

# Terraform (optional - for IaC)
sudo apt-get install terraform
```

### 3. Azure Resource Providers

```bash
# Register required providers
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.ContainerRegistry
az provider register --namespace Microsoft.DBforPostgreSQL
az provider register --namespace Microsoft.Cache
az provider register --namespace Microsoft.KeyVault
```

---

## Infrastructure Setup

### Step 1: Create Resource Group

```bash
# Variables
RESOURCE_GROUP="agentstudio-rg"
LOCATION="uaenorth"  # or your preferred region

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION
```

### Step 2: Create Container Registry

```bash
ACR_NAME="agentstudioacr"

# Create ACR
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true

# Get ACR credentials
az acr credential show --name $ACR_NAME
```

### Step 3: Create PostgreSQL Database

```bash
PG_SERVER_NAME="agentstudio-db"
PG_ADMIN_USER="agentadmin"
PG_ADMIN_PASSWORD="YourSecurePassword123!"

# Create PostgreSQL Flexible Server
az postgres flexible-server create \
  --resource-group $RESOURCE_GROUP \
  --name $PG_SERVER_NAME \
  --location $LOCATION \
  --admin-user $PG_ADMIN_USER \
  --admin-password $PG_ADMIN_PASSWORD \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 15 \
  --public-access 0.0.0.0

# Create database
az postgres flexible-server db create \
  --resource-group $RESOURCE_GROUP \
  --server-name $PG_SERVER_NAME \
  --database-name agentstudio

# Get connection string
echo "postgresql+asyncpg://$PG_ADMIN_USER:$PG_ADMIN_PASSWORD@$PG_SERVER_NAME.postgres.database.azure.com:5432/agentstudio?sslmode=require"
```

### Step 4: Create Redis Cache

```bash
REDIS_NAME="agentstudio-redis"

# Create Redis Cache
az redis create \
  --resource-group $RESOURCE_GROUP \
  --name $REDIS_NAME \
  --location $LOCATION \
  --sku Basic \
  --vm-size c0

# Get Redis connection string
az redis list-keys --resource-group $RESOURCE_GROUP --name $REDIS_NAME
```

### Step 5: Create Key Vault

```bash
KV_NAME="agentstudio-kv"

# Create Key Vault
az keyvault create \
  --resource-group $RESOURCE_GROUP \
  --name $KV_NAME \
  --location $LOCATION \
  --enable-rbac-authorization true

# Add secrets
az keyvault secret set --vault-name $KV_NAME --name "DATABASE-URL" --value "your-connection-string"
az keyvault secret set --vault-name $KV_NAME --name "REDIS-URL" --value "your-redis-connection-string"
az keyvault secret set --vault-name $KV_NAME --name "SECRET-KEY" --value "your-jwt-secret"
az keyvault secret set --vault-name $KV_NAME --name "OPENAI-API-KEY" --value "sk-..."
az keyvault secret set --vault-name $KV_NAME --name "ANTHROPIC-API-KEY" --value "sk-ant-..."
```

### Step 6: Create Container Apps Environment

```bash
ENVIRONMENT_NAME="agentstudio-env"
LOG_ANALYTICS_WORKSPACE="agentstudio-logs"

# Create Log Analytics Workspace
az monitor log-analytics workspace create \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $LOG_ANALYTICS_WORKSPACE

# Get workspace credentials
LOG_ANALYTICS_WORKSPACE_ID=$(az monitor log-analytics workspace show \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $LOG_ANALYTICS_WORKSPACE \
  --query customerId -o tsv)

LOG_ANALYTICS_KEY=$(az monitor log-analytics workspace get-shared-keys \
  --resource-group $RESOURCE_GROUP \
  --workspace-name $LOG_ANALYTICS_WORKSPACE \
  --query primarySharedKey -o tsv)

# Create Container Apps Environment
az containerapp env create \
  --resource-group $RESOURCE_GROUP \
  --name $ENVIRONMENT_NAME \
  --location $LOCATION \
  --logs-workspace-id $LOG_ANALYTICS_WORKSPACE_ID \
  --logs-workspace-key $LOG_ANALYTICS_KEY
```

### Step 7: Deploy Container Apps

#### Backend API

```bash
# Build and push backend image
az acr build \
  --registry $ACR_NAME \
  --image agentstudio-backend:latest \
  --file backend/Dockerfile \
  ./backend

# Deploy backend
az containerapp create \
  --resource-group $RESOURCE_GROUP \
  --name agentstudio-backend \
  --environment $ENVIRONMENT_NAME \
  --image $ACR_NAME.azurecr.io/agentstudio-backend:latest \
  --registry-server $ACR_NAME.azurecr.io \
  --registry-username $ACR_NAME \
  --registry-password $(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv) \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 10 \
  --cpu 0.5 \
  --memory 1.0Gi \
  --env-vars \
    DATABASE_URL=secretref:database-url \
    REDIS_URL=secretref:redis-url \
    SECRET_KEY=secretref:secret-key \
    OPENAI_API_KEY=secretref:openai-api-key \
    DEBUG=false
```

#### Frontend App

```bash
# Build and push frontend image
az acr build \
  --registry $ACR_NAME \
  --image agentstudio-frontend:latest \
  --file frontend/Dockerfile \
  ./frontend

# Deploy frontend
az containerapp create \
  --resource-group $RESOURCE_GROUP \
  --name agentstudio-frontend \
  --environment $ENVIRONMENT_NAME \
  --image $ACR_NAME.azurecr.io/agentstudio-frontend:latest \
  --registry-server $ACR_NAME.azurecr.io \
  --registry-username $ACR_NAME \
  --registry-password $(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv) \
  --target-port 80 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 5 \
  --cpu 0.25 \
  --memory 0.5Gi \
  --env-vars \
    VITE_API_BASE_URL=https://agentstudio-backend.azurecontainerapps.io
```

---

## CI/CD Pipeline Setup

### Option 1: GitHub Actions (Recommended)

#### Directory Structure

```
.github/
└── workflows/
    ├── backend-ci.yml      # Backend CI pipeline
    ├── frontend-ci.yml     # Frontend CI pipeline
    ├── deploy-staging.yml  # Staging deployment
    └── deploy-prod.yml     # Production deployment
```

#### Backend CI Pipeline

```yaml
# .github/workflows/backend-ci.yml
name: Backend CI

on:
  push:
    branches: [main, development]
    paths:
      - 'backend/**'
      - '.github/workflows/backend-ci.yml'
  pull_request:
    branches: [main, development]
    paths:
      - 'backend/**'

env:
  REGISTRY: ${{ secrets.ACR_LOGIN_SERVER }}
  IMAGE_NAME: agentstudio-backend

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        working-directory: ./backend
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov

      - name: Run linting
        working-directory: ./backend
        run: |
          pip install flake8
          flake8 app --count --select=E9,F63,F7,F82 --show-source --statistics

      - name: Run tests
        working-directory: ./backend
        run: |
          pytest tests/ -v --cov=app --cov-report=xml
        env:
          DATABASE_URL: sqlite+aiosqlite:///./test.db
          REDIS_URL: redis://localhost:6379/0
          SECRET_KEY: test-secret-key

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./backend/coverage.xml

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push'

    steps:
      - uses: actions/checkout@v4

      - name: Log in to Azure Container Registry
        uses: azure/docker-login@v1
        with:
          login-server: ${{ secrets.ACR_LOGIN_SERVER }}
          username: ${{ secrets.ACR_USERNAME }}
          password: ${{ secrets.ACR_PASSWORD }}

      - name: Build and push Docker image
        working-directory: ./backend
        run: |
          docker build -t $REGISTRY/$IMAGE_NAME:${{ github.sha }} .
          docker tag $REGISTRY/$IMAGE_NAME:${{ github.sha }} $REGISTRY/$IMAGE_NAME:latest
          docker push $REGISTRY/$IMAGE_NAME:${{ github.sha }}
          docker push $REGISTRY/$IMAGE_NAME:latest
```

#### Frontend CI Pipeline

```yaml
# .github/workflows/frontend-ci.yml
name: Frontend CI

on:
  push:
    branches: [main, development]
    paths:
      - 'frontend/**'
      - '.github/workflows/frontend-ci.yml'
  pull_request:
    branches: [main, development]
    paths:
      - 'frontend/**'

env:
  REGISTRY: ${{ secrets.ACR_LOGIN_SERVER }}
  IMAGE_NAME: agentstudio-frontend

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        working-directory: ./frontend
        run: npm ci

      - name: Run linting
        working-directory: ./frontend
        run: npm run lint

      - name: Run type check
        working-directory: ./frontend
        run: npm run type-check || true

      - name: Run tests
        working-directory: ./frontend
        run: npm test -- --passWithNoTests

      - name: Build
        working-directory: ./frontend
        run: npm run build
        env:
          VITE_API_BASE_URL: https://api.agentstudio.com

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push'

    steps:
      - uses: actions/checkout@v4

      - name: Log in to Azure Container Registry
        uses: azure/docker-login@v1
        with:
          login-server: ${{ secrets.ACR_LOGIN_SERVER }}
          username: ${{ secrets.ACR_USERNAME }}
          password: ${{ secrets.ACR_PASSWORD }}

      - name: Build and push Docker image
        working-directory: ./frontend
        run: |
          docker build \
            --build-arg VITE_API_BASE_URL=${{ secrets.API_BASE_URL }} \
            -t $REGISTRY/$IMAGE_NAME:${{ github.sha }} .
          docker tag $REGISTRY/$IMAGE_NAME:${{ github.sha }} $REGISTRY/$IMAGE_NAME:latest
          docker push $REGISTRY/$IMAGE_NAME:${{ github.sha }}
          docker push $REGISTRY/$IMAGE_NAME:latest
```

#### Staging Deployment Pipeline

```yaml
# .github/workflows/deploy-staging.yml
name: Deploy to Staging

on:
  push:
    branches: [development]
  workflow_dispatch:

env:
  AZURE_RESOURCE_GROUP: agentstudio-staging-rg
  BACKEND_APP_NAME: agentstudio-backend-staging
  FRONTEND_APP_NAME: agentstudio-frontend-staging

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Deploy Backend
        uses: azure/container-apps-deploy-action@v1
        with:
          resourceGroup: ${{ env.AZURE_RESOURCE_GROUP }}
          containerAppName: ${{ env.BACKEND_APP_NAME }}
          imageToDeploy: ${{ secrets.ACR_LOGIN_SERVER }}/agentstudio-backend:${{ github.sha }}

  deploy-frontend:
    runs-on: ubuntu-latest
    needs: deploy-backend
    steps:
      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Deploy Frontend
        uses: azure/container-apps-deploy-action@v1
        with:
          resourceGroup: ${{ env.AZURE_RESOURCE_GROUP }}
          containerAppName: ${{ env.FRONTEND_APP_NAME }}
          imageToDeploy: ${{ secrets.ACR_LOGIN_SERVER }}/agentstudio-frontend:${{ github.sha }}

  run-migrations:
    runs-on: ubuntu-latest
    needs: deploy-backend
    steps:
      - uses: actions/checkout@v4

      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Run Database Migrations
        run: |
          az containerapp exec \
            --resource-group ${{ env.AZURE_RESOURCE_GROUP }} \
            --name ${{ env.BACKEND_APP_NAME }} \
            --command "alembic upgrade head"
```

#### Production Deployment Pipeline

```yaml
# .github/workflows/deploy-prod.yml
name: Deploy to Production

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:
    inputs:
      image_tag:
        description: 'Image tag to deploy'
        required: true
        default: 'latest'

env:
  AZURE_RESOURCE_GROUP: agentstudio-prod-rg
  BACKEND_APP_NAME: agentstudio-backend
  FRONTEND_APP_NAME: agentstudio-frontend

jobs:
  approve:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Deployment Approval
        run: echo "Deployment approved"

  deploy-backend:
    runs-on: ubuntu-latest
    needs: approve
    steps:
      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS_PROD }}

      - name: Deploy Backend
        uses: azure/container-apps-deploy-action@v1
        with:
          resourceGroup: ${{ env.AZURE_RESOURCE_GROUP }}
          containerAppName: ${{ env.BACKEND_APP_NAME }}
          imageToDeploy: ${{ secrets.ACR_LOGIN_SERVER }}/agentstudio-backend:${{ github.event.inputs.image_tag || github.ref_name }}

      - name: Health Check
        run: |
          sleep 30
          curl -f https://agentstudio-backend.azurecontainerapps.io/health || exit 1

  deploy-frontend:
    runs-on: ubuntu-latest
    needs: deploy-backend
    steps:
      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS_PROD }}

      - name: Deploy Frontend
        uses: azure/container-apps-deploy-action@v1
        with:
          resourceGroup: ${{ env.AZURE_RESOURCE_GROUP }}
          containerAppName: ${{ env.FRONTEND_APP_NAME }}
          imageToDeploy: ${{ secrets.ACR_LOGIN_SERVER }}/agentstudio-frontend:${{ github.event.inputs.image_tag || github.ref_name }}

  notify:
    runs-on: ubuntu-latest
    needs: [deploy-backend, deploy-frontend]
    if: always()
    steps:
      - name: Notify on Success
        if: ${{ needs.deploy-frontend.result == 'success' }}
        run: |
          echo "Deployment successful!"
          # Add Slack/Teams notification here

      - name: Notify on Failure
        if: ${{ needs.deploy-frontend.result == 'failure' }}
        run: |
          echo "Deployment failed!"
          # Add Slack/Teams notification here
```

### Option 2: Azure DevOps Pipelines

#### Azure Pipelines YAML

```yaml
# azure-pipelines.yml
trigger:
  branches:
    include:
      - main
      - development
  paths:
    include:
      - backend/*
      - frontend/*

pool:
  vmImage: 'ubuntu-latest'

variables:
  - group: agentstudio-variables
  - name: acrName
    value: 'agentstudioacr'

stages:
  - stage: Build
    displayName: 'Build Stage'
    jobs:
      - job: BuildBackend
        displayName: 'Build Backend'
        steps:
          - task: Docker@2
            displayName: 'Build and Push Backend'
            inputs:
              containerRegistry: 'ACR-Connection'
              repository: 'agentstudio-backend'
              command: 'buildAndPush'
              Dockerfile: 'backend/Dockerfile'
              buildContext: 'backend'
              tags: |
                $(Build.BuildId)
                latest

      - job: BuildFrontend
        displayName: 'Build Frontend'
        steps:
          - task: Docker@2
            displayName: 'Build and Push Frontend'
            inputs:
              containerRegistry: 'ACR-Connection'
              repository: 'agentstudio-frontend'
              command: 'buildAndPush'
              Dockerfile: 'frontend/Dockerfile'
              buildContext: 'frontend'
              tags: |
                $(Build.BuildId)
                latest

  - stage: DeployStaging
    displayName: 'Deploy to Staging'
    dependsOn: Build
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/development'))
    jobs:
      - deployment: DeployStaging
        displayName: 'Deploy to Staging Environment'
        environment: 'staging'
        strategy:
          runOnce:
            deploy:
              steps:
                - task: AzureCLI@2
                  displayName: 'Deploy Backend'
                  inputs:
                    azureSubscription: 'Azure-Subscription'
                    scriptType: 'bash'
                    scriptLocation: 'inlineScript'
                    inlineScript: |
                      az containerapp update \
                        --resource-group agentstudio-staging-rg \
                        --name agentstudio-backend-staging \
                        --image $(acrName).azurecr.io/agentstudio-backend:$(Build.BuildId)

  - stage: DeployProduction
    displayName: 'Deploy to Production'
    dependsOn: Build
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - deployment: DeployProduction
        displayName: 'Deploy to Production Environment'
        environment: 'production'
        strategy:
          runOnce:
            deploy:
              steps:
                - task: AzureCLI@2
                  displayName: 'Deploy Backend'
                  inputs:
                    azureSubscription: 'Azure-Subscription'
                    scriptType: 'bash'
                    scriptLocation: 'inlineScript'
                    inlineScript: |
                      az containerapp update \
                        --resource-group agentstudio-prod-rg \
                        --name agentstudio-backend \
                        --image $(acrName).azurecr.io/agentstudio-backend:$(Build.BuildId)
```

---

## Environment Configuration

### GitHub Secrets Setup

Navigate to Repository → Settings → Secrets and variables → Actions

| Secret Name | Description |
|-------------|-------------|
| `AZURE_CREDENTIALS` | Azure Service Principal JSON |
| `ACR_LOGIN_SERVER` | ACR server URL (e.g., agentstudioacr.azurecr.io) |
| `ACR_USERNAME` | ACR admin username |
| `ACR_PASSWORD` | ACR admin password |
| `API_BASE_URL` | Backend API URL |

### Create Azure Service Principal

```bash
# Create service principal for CI/CD
az ad sp create-for-rbac \
  --name "agentstudio-cicd" \
  --role contributor \
  --scopes /subscriptions/{subscription-id}/resourceGroups/{resource-group} \
  --sdk-auth

# Output JSON - save as AZURE_CREDENTIALS secret
```

### Container App Environment Variables

```bash
# Set environment variables for backend
az containerapp update \
  --resource-group $RESOURCE_GROUP \
  --name agentstudio-backend \
  --set-env-vars \
    "DATABASE_URL=secretref:database-url" \
    "REDIS_URL=secretref:redis-url" \
    "SECRET_KEY=secretref:secret-key" \
    "OPENAI_API_KEY=secretref:openai-api-key" \
    "ANTHROPIC_API_KEY=secretref:anthropic-api-key" \
    "DEBUG=false" \
    "CORS_ORIGINS=https://app.agentstudio.com" \
    "VOICE_WEBHOOK_IP_WHITELIST=true"
```

---

## Security Best Practices

### 1. Network Security

```bash
# Create Virtual Network for Container Apps
az network vnet create \
  --resource-group $RESOURCE_GROUP \
  --name agentstudio-vnet \
  --address-prefix 10.0.0.0/16 \
  --subnet-name container-apps-subnet \
  --subnet-prefix 10.0.0.0/23

# Configure private endpoints for PostgreSQL
az postgres flexible-server update \
  --resource-group $RESOURCE_GROUP \
  --name $PG_SERVER_NAME \
  --public-access Disabled

az network private-endpoint create \
  --resource-group $RESOURCE_GROUP \
  --name pg-private-endpoint \
  --vnet-name agentstudio-vnet \
  --subnet container-apps-subnet \
  --private-connection-resource-id $(az postgres flexible-server show --resource-group $RESOURCE_GROUP --name $PG_SERVER_NAME --query id -o tsv) \
  --group-id postgresqlServer \
  --connection-name pg-connection
```

### 2. Key Vault Integration

```bash
# Enable managed identity for Container App
az containerapp identity assign \
  --resource-group $RESOURCE_GROUP \
  --name agentstudio-backend \
  --system-assigned

# Get identity principal ID
IDENTITY_ID=$(az containerapp show \
  --resource-group $RESOURCE_GROUP \
  --name agentstudio-backend \
  --query identity.principalId -o tsv)

# Grant Key Vault access
az keyvault set-policy \
  --name $KV_NAME \
  --object-id $IDENTITY_ID \
  --secret-permissions get list
```

### 3. SSL/TLS Configuration

```bash
# Add custom domain with managed certificate
az containerapp hostname add \
  --resource-group $RESOURCE_GROUP \
  --name agentstudio-frontend \
  --hostname app.agentstudio.com

az containerapp hostname bind \
  --resource-group $RESOURCE_GROUP \
  --name agentstudio-frontend \
  --hostname app.agentstudio.com \
  --environment $ENVIRONMENT_NAME \
  --validation-method CNAME
```

---

## Monitoring & Logging

### Azure Monitor Setup

```bash
# Create Application Insights
az monitor app-insights component create \
  --resource-group $RESOURCE_GROUP \
  --app agentstudio-insights \
  --location $LOCATION \
  --workspace $LOG_ANALYTICS_WORKSPACE

# Get instrumentation key
APPINSIGHTS_KEY=$(az monitor app-insights component show \
  --resource-group $RESOURCE_GROUP \
  --app agentstudio-insights \
  --query instrumentationKey -o tsv)

# Add to Container App
az containerapp update \
  --resource-group $RESOURCE_GROUP \
  --name agentstudio-backend \
  --set-env-vars "APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=$APPINSIGHTS_KEY"
```

### Alerting Rules

```bash
# Create alert for high CPU
az monitor metrics alert create \
  --resource-group $RESOURCE_GROUP \
  --name "High CPU Alert" \
  --scopes $(az containerapp show --resource-group $RESOURCE_GROUP --name agentstudio-backend --query id -o tsv) \
  --condition "avg Percentage CPU > 80" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action-group "AlertActionGroup"

# Create alert for errors
az monitor metrics alert create \
  --resource-group $RESOURCE_GROUP \
  --name "Error Rate Alert" \
  --scopes $(az containerapp show --resource-group $RESOURCE_GROUP --name agentstudio-backend --query id -o tsv) \
  --condition "count requests/failed > 10" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action-group "AlertActionGroup"
```

---

## Cost Optimization

### Estimated Monthly Costs (USD)

| Service | SKU | Est. Cost/Month |
|---------|-----|-----------------|
| Container Apps (Backend) | Consumption (1 vCPU, 2GB) | $50-100 |
| Container Apps (Frontend) | Consumption (0.5 vCPU, 1GB) | $25-50 |
| PostgreSQL Flexible Server | Burstable B1ms | $15-30 |
| Redis Cache | Basic C0 | $16 |
| Container Registry | Basic | $5 |
| Key Vault | Standard | $3 |
| Log Analytics | Pay-as-you-go | $10-20 |
| **Total Estimated** | | **$125-225/month** |

### Cost Saving Tips

1. **Use Spot Instances** for non-critical workloads
2. **Scale to zero** during off-hours
3. **Right-size** container resources based on metrics
4. **Use reserved capacity** for predictable workloads
5. **Enable auto-scaling** with appropriate min/max replicas

```bash
# Configure scale to zero for staging
az containerapp update \
  --resource-group agentstudio-staging-rg \
  --name agentstudio-backend-staging \
  --min-replicas 0 \
  --max-replicas 3

# Configure auto-scaling based on HTTP requests
az containerapp update \
  --resource-group $RESOURCE_GROUP \
  --name agentstudio-backend \
  --scale-rule-name http-scaling \
  --scale-rule-type http \
  --scale-rule-http-concurrency 100
```

---

## Quick Start Commands

```bash
# Full deployment script
./scripts/deploy-azure.sh

# Deploy only backend
az containerapp update -g $RG -n agentstudio-backend --image $ACR/backend:latest

# View logs
az containerapp logs show -g $RG -n agentstudio-backend --follow

# Restart app
az containerapp revision restart -g $RG -n agentstudio-backend

# Scale manually
az containerapp update -g $RG -n agentstudio-backend --min-replicas 2 --max-replicas 10
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Container fails to start | Check logs: `az containerapp logs show` |
| Database connection fails | Verify firewall rules, connection string |
| Redis connection timeout | Check Redis firewall, use private endpoint |
| SSL certificate issues | Verify DNS propagation, use managed certs |
| High memory usage | Increase container memory, optimize code |

### Useful Commands

```bash
# Check container status
az containerapp show -g $RG -n agentstudio-backend --query properties.runningStatus

# Get container logs
az containerapp logs show -g $RG -n agentstudio-backend --tail 100

# Execute command in container
az containerapp exec -g $RG -n agentstudio-backend --command "/bin/bash"

# Check revisions
az containerapp revision list -g $RG -n agentstudio-backend -o table
```

---

## Next Steps

1. Set up Azure Front Door for global load balancing
2. Configure Azure WAF for security
3. Implement blue-green deployments
4. Set up disaster recovery in secondary region
5. Configure backup policies for PostgreSQL

---

**Last Updated**: January 2025
**Maintained By**: AgentStudio DevOps Team
