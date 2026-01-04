#!/bin/bash
# AgentStudio Azure Deployment Script
# This script sets up all Azure resources for AgentStudio

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  AgentStudio Azure Deployment Script  ${NC}"
echo -e "${GREEN}========================================${NC}"

# Configuration - MODIFY THESE VALUES
RESOURCE_GROUP="${RESOURCE_GROUP:-agentstudio-rg}"
LOCATION="${LOCATION:-uaenorth}"
ACR_NAME="${ACR_NAME:-agentstudioacr}"
PG_SERVER_NAME="${PG_SERVER_NAME:-agentstudio-db}"
REDIS_NAME="${REDIS_NAME:-agentstudio-redis}"
KV_NAME="${KV_NAME:-agentstudio-kv}"
ENVIRONMENT_NAME="${ENVIRONMENT_NAME:-agentstudio-env}"
LOG_ANALYTICS_WORKSPACE="${LOG_ANALYTICS_WORKSPACE:-agentstudio-logs}"

# Database credentials
PG_ADMIN_USER="${PG_ADMIN_USER:-agentadmin}"
PG_ADMIN_PASSWORD="${PG_ADMIN_PASSWORD:-$(openssl rand -base64 24)}"

# JWT Secret
SECRET_KEY="${SECRET_KEY:-$(openssl rand -hex 32)}"

echo -e "\n${YELLOW}Configuration:${NC}"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Location: $LOCATION"
echo "  ACR Name: $ACR_NAME"
echo "  PostgreSQL: $PG_SERVER_NAME"
echo "  Redis: $REDIS_NAME"
echo ""

# Function to check if logged in
check_azure_login() {
    echo -e "\n${YELLOW}Step 0: Checking Azure CLI login...${NC}"
    if ! az account show &> /dev/null; then
        echo -e "${RED}Not logged in to Azure CLI. Please run: az login${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Logged in to Azure${NC}"
    az account show --query "{Subscription:name, TenantId:tenantId}" -o table
}

# Step 1: Create Resource Group
create_resource_group() {
    echo -e "\n${YELLOW}Step 1: Creating Resource Group...${NC}"
    az group create --name $RESOURCE_GROUP --location $LOCATION -o none
    echo -e "${GREEN}✓ Resource Group created: $RESOURCE_GROUP${NC}"
}

# Step 2: Create Container Registry
create_acr() {
    echo -e "\n${YELLOW}Step 2: Creating Azure Container Registry...${NC}"
    az acr create \
        --resource-group $RESOURCE_GROUP \
        --name $ACR_NAME \
        --sku Basic \
        --admin-enabled true \
        -o none
    echo -e "${GREEN}✓ Container Registry created: $ACR_NAME${NC}"

    # Get ACR credentials
    ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)
    ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username -o tsv)
    ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv)

    echo -e "${GREEN}  ACR Server: $ACR_LOGIN_SERVER${NC}"
}

# Step 3: Create PostgreSQL
create_postgresql() {
    echo -e "\n${YELLOW}Step 3: Creating PostgreSQL Flexible Server...${NC}"
    az postgres flexible-server create \
        --resource-group $RESOURCE_GROUP \
        --name $PG_SERVER_NAME \
        --location $LOCATION \
        --admin-user $PG_ADMIN_USER \
        --admin-password "$PG_ADMIN_PASSWORD" \
        --sku-name Standard_B1ms \
        --tier Burstable \
        --storage-size 32 \
        --version 15 \
        --public-access 0.0.0.0 \
        -o none

    # Create database
    az postgres flexible-server db create \
        --resource-group $RESOURCE_GROUP \
        --server-name $PG_SERVER_NAME \
        --database-name agentstudio \
        -o none

    DATABASE_URL="postgresql+asyncpg://$PG_ADMIN_USER:$PG_ADMIN_PASSWORD@$PG_SERVER_NAME.postgres.database.azure.com:5432/agentstudio?sslmode=require"
    echo -e "${GREEN}✓ PostgreSQL created: $PG_SERVER_NAME${NC}"
}

# Step 4: Create Redis Cache
create_redis() {
    echo -e "\n${YELLOW}Step 4: Creating Redis Cache...${NC}"
    az redis create \
        --resource-group $RESOURCE_GROUP \
        --name $REDIS_NAME \
        --location $LOCATION \
        --sku Basic \
        --vm-size c0 \
        -o none

    REDIS_KEY=$(az redis list-keys --resource-group $RESOURCE_GROUP --name $REDIS_NAME --query primaryKey -o tsv)
    REDIS_URL="rediss://:$REDIS_KEY@$REDIS_NAME.redis.cache.windows.net:6380/0"
    echo -e "${GREEN}✓ Redis Cache created: $REDIS_NAME${NC}"
}

# Step 5: Create Key Vault
create_keyvault() {
    echo -e "\n${YELLOW}Step 5: Creating Key Vault...${NC}"
    az keyvault create \
        --resource-group $RESOURCE_GROUP \
        --name $KV_NAME \
        --location $LOCATION \
        -o none

    # Add secrets
    az keyvault secret set --vault-name $KV_NAME --name "DATABASE-URL" --value "$DATABASE_URL" -o none
    az keyvault secret set --vault-name $KV_NAME --name "REDIS-URL" --value "$REDIS_URL" -o none
    az keyvault secret set --vault-name $KV_NAME --name "SECRET-KEY" --value "$SECRET_KEY" -o none

    echo -e "${GREEN}✓ Key Vault created: $KV_NAME${NC}"
}

# Step 6: Create Log Analytics Workspace
create_log_analytics() {
    echo -e "\n${YELLOW}Step 6: Creating Log Analytics Workspace...${NC}"
    az monitor log-analytics workspace create \
        --resource-group $RESOURCE_GROUP \
        --workspace-name $LOG_ANALYTICS_WORKSPACE \
        -o none

    LOG_ANALYTICS_WORKSPACE_ID=$(az monitor log-analytics workspace show \
        --resource-group $RESOURCE_GROUP \
        --workspace-name $LOG_ANALYTICS_WORKSPACE \
        --query customerId -o tsv)

    LOG_ANALYTICS_KEY=$(az monitor log-analytics workspace get-shared-keys \
        --resource-group $RESOURCE_GROUP \
        --workspace-name $LOG_ANALYTICS_WORKSPACE \
        --query primarySharedKey -o tsv)

    echo -e "${GREEN}✓ Log Analytics Workspace created${NC}"
}

# Step 7: Create Container Apps Environment
create_container_apps_env() {
    echo -e "\n${YELLOW}Step 7: Creating Container Apps Environment...${NC}"
    az containerapp env create \
        --resource-group $RESOURCE_GROUP \
        --name $ENVIRONMENT_NAME \
        --location $LOCATION \
        --logs-workspace-id $LOG_ANALYTICS_WORKSPACE_ID \
        --logs-workspace-key $LOG_ANALYTICS_KEY \
        -o none

    echo -e "${GREEN}✓ Container Apps Environment created: $ENVIRONMENT_NAME${NC}"
}

# Step 8: Build and Push Docker Images
build_and_push_images() {
    echo -e "\n${YELLOW}Step 8: Building and Pushing Docker Images...${NC}"

    # Login to ACR
    az acr login --name $ACR_NAME

    # Build and push backend
    echo "Building backend..."
    az acr build \
        --registry $ACR_NAME \
        --image agentstudio-backend:latest \
        --file backend/Dockerfile \
        ./backend

    # Build and push frontend
    echo "Building frontend..."
    az acr build \
        --registry $ACR_NAME \
        --image agentstudio-frontend:latest \
        --file frontend/Dockerfile \
        --build-arg VITE_API_BASE_URL=https://agentstudio-backend.${LOCATION}.azurecontainerapps.io \
        ./frontend

    echo -e "${GREEN}✓ Docker images built and pushed${NC}"
}

# Step 9: Deploy Container Apps
deploy_container_apps() {
    echo -e "\n${YELLOW}Step 9: Deploying Container Apps...${NC}"

    # Deploy backend
    az containerapp create \
        --resource-group $RESOURCE_GROUP \
        --name agentstudio-backend \
        --environment $ENVIRONMENT_NAME \
        --image $ACR_LOGIN_SERVER/agentstudio-backend:latest \
        --registry-server $ACR_LOGIN_SERVER \
        --registry-username $ACR_USERNAME \
        --registry-password $ACR_PASSWORD \
        --target-port 8000 \
        --ingress external \
        --min-replicas 1 \
        --max-replicas 10 \
        --cpu 0.5 \
        --memory 1.0Gi \
        --env-vars \
            "DATABASE_URL=$DATABASE_URL" \
            "REDIS_URL=$REDIS_URL" \
            "SECRET_KEY=$SECRET_KEY" \
            "DEBUG=false" \
            "CORS_ORIGINS=*" \
        -o none

    BACKEND_URL=$(az containerapp show \
        --resource-group $RESOURCE_GROUP \
        --name agentstudio-backend \
        --query properties.configuration.ingress.fqdn -o tsv)

    echo -e "${GREEN}✓ Backend deployed: https://$BACKEND_URL${NC}"

    # Deploy frontend
    az containerapp create \
        --resource-group $RESOURCE_GROUP \
        --name agentstudio-frontend \
        --environment $ENVIRONMENT_NAME \
        --image $ACR_LOGIN_SERVER/agentstudio-frontend:latest \
        --registry-server $ACR_LOGIN_SERVER \
        --registry-username $ACR_USERNAME \
        --registry-password $ACR_PASSWORD \
        --target-port 80 \
        --ingress external \
        --min-replicas 1 \
        --max-replicas 5 \
        --cpu 0.25 \
        --memory 0.5Gi \
        -o none

    FRONTEND_URL=$(az containerapp show \
        --resource-group $RESOURCE_GROUP \
        --name agentstudio-frontend \
        --query properties.configuration.ingress.fqdn -o tsv)

    echo -e "${GREEN}✓ Frontend deployed: https://$FRONTEND_URL${NC}"
}

# Step 10: Run database migrations
run_migrations() {
    echo -e "\n${YELLOW}Step 10: Running Database Migrations...${NC}"
    az containerapp exec \
        --resource-group $RESOURCE_GROUP \
        --name agentstudio-backend \
        --command "alembic upgrade head" || echo "Migrations may need manual execution"
    echo -e "${GREEN}✓ Migrations completed${NC}"
}

# Save credentials to file
save_credentials() {
    echo -e "\n${YELLOW}Saving credentials...${NC}"

    cat > .azure-credentials.env << EOF
# Azure Credentials - KEEP SECRET!
# Generated on $(date)

# Resource Group
RESOURCE_GROUP=$RESOURCE_GROUP
LOCATION=$LOCATION

# Container Registry
ACR_NAME=$ACR_NAME
ACR_LOGIN_SERVER=$ACR_LOGIN_SERVER
ACR_USERNAME=$ACR_USERNAME
ACR_PASSWORD=$ACR_PASSWORD

# PostgreSQL
PG_SERVER_NAME=$PG_SERVER_NAME
PG_ADMIN_USER=$PG_ADMIN_USER
PG_ADMIN_PASSWORD=$PG_ADMIN_PASSWORD
DATABASE_URL=$DATABASE_URL

# Redis
REDIS_NAME=$REDIS_NAME
REDIS_URL=$REDIS_URL

# Security
SECRET_KEY=$SECRET_KEY

# Key Vault
KV_NAME=$KV_NAME

# Container Apps
ENVIRONMENT_NAME=$ENVIRONMENT_NAME
BACKEND_URL=https://$BACKEND_URL
FRONTEND_URL=https://$FRONTEND_URL

# GitHub Secrets (add these to your repository)
# ACR_LOGIN_SERVER=$ACR_LOGIN_SERVER
# ACR_USERNAME=$ACR_USERNAME
# ACR_PASSWORD=$ACR_PASSWORD
# API_BASE_URL=https://$BACKEND_URL
EOF

    chmod 600 .azure-credentials.env
    echo -e "${GREEN}✓ Credentials saved to .azure-credentials.env${NC}"
    echo -e "${RED}⚠️  Keep this file secure and don't commit to git!${NC}"
}

# Print summary
print_summary() {
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}       Deployment Complete!             ${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "Frontend URL: ${GREEN}https://$FRONTEND_URL${NC}"
    echo -e "Backend URL:  ${GREEN}https://$BACKEND_URL${NC}"
    echo -e "API Docs:     ${GREEN}https://$BACKEND_URL/docs${NC}"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "1. Add GitHub Secrets for CI/CD (see .azure-credentials.env)"
    echo "2. Configure custom domain (optional)"
    echo "3. Add your LLM API keys in the Credentials page"
    echo "4. Create your first agent!"
    echo ""
}

# Main execution
main() {
    check_azure_login
    create_resource_group
    create_acr
    create_postgresql
    create_redis
    create_keyvault
    create_log_analytics
    create_container_apps_env
    build_and_push_images
    deploy_container_apps
    run_migrations
    save_credentials
    print_summary
}

# Run main function
main
