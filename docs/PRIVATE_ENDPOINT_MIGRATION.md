# Private Endpoint Migration Guide

This document outlines the infrastructure changes required to migrate AgentStudio to a VNet-integrated architecture with private endpoints for enhanced security.

## Current Architecture

```
Internet ──► Front Door ──► Container Apps (Managed Network) ──► Redis (Public)
                                      │
                                      └──► PostgreSQL (Public)
```

**Issues:**
- Redis and PostgreSQL are publicly accessible
- No network isolation
- Security risk for production workloads

---

## Target Architecture

```
                         ┌─────────────────────────────────────────────────┐
                         │              VNet (10.0.0.0/16)                 │
                         │                                                 │
Internet ◄───────────────┤  ┌─────────────────────────────────────────┐   │
(OpenAI, Anthropic,      │  │  Container Apps Subnet (10.0.0.0/23)    │   │
 External APIs)          │  │  - agentstudio-backend                  │   │
         ▲               │  │  - agentstudio-frontend                 │   │
         │               │  └──────────────┬──────────────────────────┘   │
         │               │                 │                               │
    NAT Gateway          │                 │ Private Endpoints             │
    (10.0.3.0/24)        │                 ▼                               │
         │               │  ┌─────────────────────────────────────────┐   │
         │               │  │  Private Endpoint Subnet (10.0.2.0/24)  │   │
         │               │  │  - Redis Private Endpoint               │   │
         │               │  │  - PostgreSQL Private Endpoint          │   │
         │               │  └─────────────────────────────────────────┘   │
         │               └─────────────────────────────────────────────────┘
         │
    ┌────┴────┐
    │   NAT   │◄── Static Outbound IP
    │ Gateway │
    └─────────┘
```

---

## Prerequisites

- Azure CLI installed and logged in
- Owner/Contributor access to `agentstudio-rg` resource group
- Current environment details backed up

---

## Step 1: Create Virtual Network

Create a VNet with sufficient address space for all subnets.

```bash
az network vnet create \
  --name agentstudio-vnet \
  --resource-group agentstudio-rg \
  --location "UAE North" \
  --address-prefix 10.0.0.0/16
```

**Verification:**
```bash
az network vnet show --name agentstudio-vnet --resource-group agentstudio-rg --query "{name:name, addressSpace:addressSpace}" -o table
```

---

## Step 2: Create Subnets

### 2.1 Container Apps Subnet

Container Apps requires a minimum of /23 subnet (512 IPs).

```bash
az network vnet subnet create \
  --name containerapp-subnet \
  --vnet-name agentstudio-vnet \
  --resource-group agentstudio-rg \
  --address-prefixes 10.0.0.0/23
```

### 2.2 Private Endpoint Subnet

For Redis and PostgreSQL private endpoints.

```bash
az network vnet subnet create \
  --name privateendpoint-subnet \
  --vnet-name agentstudio-vnet \
  --resource-group agentstudio-rg \
  --address-prefixes 10.0.2.0/24 \
  --disable-private-endpoint-network-policies true
```

### 2.3 NAT Gateway Subnet (Optional but Recommended)

```bash
az network vnet subnet create \
  --name nat-subnet \
  --vnet-name agentstudio-vnet \
  --resource-group agentstudio-rg \
  --address-prefixes 10.0.3.0/24
```

**Verification:**
```bash
az network vnet subnet list --vnet-name agentstudio-vnet --resource-group agentstudio-rg -o table
```

---

## Step 3: Create NAT Gateway (Recommended)

NAT Gateway provides reliable outbound internet connectivity with static IPs.

### 3.1 Create Public IP for NAT

```bash
az network public-ip create \
  --name agentstudio-nat-ip \
  --resource-group agentstudio-rg \
  --location "UAE North" \
  --sku Standard \
  --allocation-method Static
```

### 3.2 Create NAT Gateway

```bash
az network nat gateway create \
  --name agentstudio-nat \
  --resource-group agentstudio-rg \
  --location "UAE North" \
  --public-ip-addresses agentstudio-nat-ip \
  --idle-timeout 10
```

### 3.3 Associate NAT Gateway with Container Apps Subnet

```bash
az network vnet subnet update \
  --name containerapp-subnet \
  --vnet-name agentstudio-vnet \
  --resource-group agentstudio-rg \
  --nat-gateway agentstudio-nat
```

**Verification:**
```bash
az network nat gateway show --name agentstudio-nat --resource-group agentstudio-rg -o table
```

---

## Step 4: Create Private DNS Zones

### 4.1 Redis Private DNS Zone

```bash
az network private-dns zone create \
  --name privatelink.redis.cache.windows.net \
  --resource-group agentstudio-rg
```

### 4.2 PostgreSQL Private DNS Zone

```bash
az network private-dns zone create \
  --name privatelink.postgres.database.azure.com \
  --resource-group agentstudio-rg
```

### 4.3 Link DNS Zones to VNet

```bash
# Redis DNS link
az network private-dns link vnet create \
  --name redis-dns-link \
  --resource-group agentstudio-rg \
  --zone-name privatelink.redis.cache.windows.net \
  --virtual-network agentstudio-vnet \
  --registration-enabled false

# PostgreSQL DNS link
az network private-dns link vnet create \
  --name postgres-dns-link \
  --resource-group agentstudio-rg \
  --zone-name privatelink.postgres.database.azure.com \
  --virtual-network agentstudio-vnet \
  --registration-enabled false
```

**Verification:**
```bash
az network private-dns zone list --resource-group agentstudio-rg -o table
```

---

## Step 5: Create Private Endpoints

### 5.1 Redis Private Endpoint

```bash
# Get Redis resource ID
REDIS_ID=$(az redis show --name agentstudio-redis --resource-group agentstudio-rg --query id -o tsv)

# Create private endpoint
az network private-endpoint create \
  --name agentstudio-redis-pe \
  --resource-group agentstudio-rg \
  --location "UAE North" \
  --vnet-name agentstudio-vnet \
  --subnet privateendpoint-subnet \
  --private-connection-resource-id $REDIS_ID \
  --group-id redisCache \
  --connection-name redis-connection

# Register with private DNS
az network private-endpoint dns-zone-group create \
  --endpoint-name agentstudio-redis-pe \
  --resource-group agentstudio-rg \
  --name redis-dns-group \
  --private-dns-zone privatelink.redis.cache.windows.net \
  --zone-name privatelink.redis.cache.windows.net
```

### 5.2 PostgreSQL Private Endpoint

```bash
# Get PostgreSQL resource ID
POSTGRES_ID=$(az postgres flexible-server show --name agentstudio-db --resource-group agentstudio-rg --query id -o tsv)

# Create private endpoint
az network private-endpoint create \
  --name agentstudio-postgres-pe \
  --resource-group agentstudio-rg \
  --location "UAE North" \
  --vnet-name agentstudio-vnet \
  --subnet privateendpoint-subnet \
  --private-connection-resource-id $POSTGRES_ID \
  --group-id postgresqlServer \
  --connection-name postgres-connection

# Register with private DNS
az network private-endpoint dns-zone-group create \
  --endpoint-name agentstudio-postgres-pe \
  --resource-group agentstudio-rg \
  --name postgres-dns-group \
  --private-dns-zone privatelink.postgres.database.azure.com \
  --zone-name privatelink.postgres.database.azure.com
```

**Verification:**
```bash
az network private-endpoint list --resource-group agentstudio-rg -o table
```

---

## Step 6: Create New Container Apps Environment

The existing environment cannot be updated with VNet integration - a new one must be created.

### 6.1 Get Subnet ID

```bash
SUBNET_ID=$(az network vnet subnet show \
  --name containerapp-subnet \
  --vnet-name agentstudio-vnet \
  --resource-group agentstudio-rg \
  --query id -o tsv)

echo $SUBNET_ID
```

### 6.2 Create New Environment

```bash
az containerapp env create \
  --name agentstudio-env-v2 \
  --resource-group agentstudio-rg \
  --location "UAE North" \
  --infrastructure-subnet-resource-id $SUBNET_ID \
  --internal-only false \
  --logs-workspace-id $(az containerapp env show --name agentstudio-env --resource-group agentstudio-rg --query "properties.appLogsConfiguration.logAnalyticsConfiguration.customerId" -o tsv)
```

**Verification:**
```bash
az containerapp env show --name agentstudio-env-v2 --resource-group agentstudio-rg --query "{name:name, provisioningState:properties.provisioningState, vnetId:properties.vnetConfiguration}" -o json
```

---

## Step 7: Export Current Container Apps Configuration

Before migration, export current app configurations.

### 7.1 Export Backend Configuration

```bash
az containerapp show --name agentstudio-backend --resource-group agentstudio-rg -o json > backup-backend.json
```

### 7.2 Export Frontend Configuration

```bash
az containerapp show --name agentstudio-frontend --resource-group agentstudio-rg -o json > backup-frontend.json
```

### 7.3 Note Current Environment Variables

```bash
az containerapp show --name agentstudio-backend --resource-group agentstudio-rg --query "properties.template.containers[0].env" -o json > backup-backend-env.json
```

---

## Step 8: Migrate Container Apps

### 8.1 Create Backend in New Environment

```bash
az containerapp create \
  --name agentstudio-backend \
  --resource-group agentstudio-rg \
  --environment agentstudio-env-v2 \
  --image agentstudioacr.azurecr.io/agentstudio-backend:development \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 10 \
  --cpu 0.5 \
  --memory 1.0Gi \
  --registry-server agentstudioacr.azurecr.io \
  --registry-username agentstudioacr \
  --registry-password <ACR_PASSWORD> \
  --env-vars \
    SECRET_KEY=<SECRET_KEY> \
    DATABASE_URL="postgresql+asyncpg://agentadmin:<PASSWORD>@agentstudio-db.postgres.database.azure.com/agentstudio?ssl=require" \
    REDIS_URL="rediss://:23IcPSjv2JhDgl7JRxrUyAPDKAEuqwCviAzCaH8q2Vo=@agentstudio-redis.redis.cache.windows.net:6380/" \
    VOICE_WEBHOOK_ALLOW_ALL=true
```

### 8.2 Create Frontend in New Environment

```bash
az containerapp create \
  --name agentstudio-frontend \
  --resource-group agentstudio-rg \
  --environment agentstudio-env-v2 \
  --image agentstudioacr.azurecr.io/agentstudio-frontend:development \
  --target-port 80 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 10 \
  --cpu 0.25 \
  --memory 0.5Gi \
  --registry-server agentstudioacr.azurecr.io \
  --registry-username agentstudioacr \
  --registry-password <ACR_PASSWORD>
```

**Verification:**
```bash
az containerapp list --resource-group agentstudio-rg --query "[].{name:name, environment:properties.environmentId, fqdn:properties.configuration.ingress.fqdn}" -o table
```

---

## Step 9: Disable Public Access on Services

Only do this AFTER verifying apps work in new environment.

### 9.1 Disable Public Access on Redis

```bash
az redis update \
  --name agentstudio-redis \
  --resource-group agentstudio-rg \
  --set publicNetworkAccess=Disabled
```

### 9.2 Disable Public Access on PostgreSQL

```bash
az postgres flexible-server update \
  --name agentstudio-db \
  --resource-group agentstudio-rg \
  --public-access Disabled
```

---

## Step 10: Update Front Door / DNS

### 10.1 Get New Backend FQDN

```bash
az containerapp show --name agentstudio-backend --resource-group agentstudio-rg --query "properties.configuration.ingress.fqdn" -o tsv
```

### 10.2 Update Front Door Backend Pool

```bash
# Get new FQDNs
BACKEND_FQDN=$(az containerapp show --name agentstudio-backend --resource-group agentstudio-rg --query "properties.configuration.ingress.fqdn" -o tsv)
FRONTEND_FQDN=$(az containerapp show --name agentstudio-frontend --resource-group agentstudio-rg --query "properties.configuration.ingress.fqdn" -o tsv)

echo "Backend FQDN: $BACKEND_FQDN"
echo "Frontend FQDN: $FRONTEND_FQDN"

# Update Front Door origins (command varies based on Front Door configuration)
# Refer to Azure Portal or specific Front Door CLI commands
```

---

## Step 11: Cleanup Old Resources

Only after confirming everything works.

### 11.1 Delete Old Container Apps Environment

```bash
# First, ensure no apps are using old environment
az containerapp env delete \
  --name agentstudio-env \
  --resource-group agentstudio-rg \
  --yes
```

---

## Verification Checklist

| Step | Verification Command | Expected Result |
|------|---------------------|-----------------|
| VNet Created | `az network vnet show --name agentstudio-vnet -g agentstudio-rg` | VNet exists |
| Subnets Created | `az network vnet subnet list --vnet-name agentstudio-vnet -g agentstudio-rg` | 3 subnets |
| NAT Gateway | `az network nat gateway show --name agentstudio-nat -g agentstudio-rg` | NAT exists |
| Private DNS Zones | `az network private-dns zone list -g agentstudio-rg` | 2 zones |
| Private Endpoints | `az network private-endpoint list -g agentstudio-rg` | 2 endpoints |
| New Environment | `az containerapp env show --name agentstudio-env-v2 -g agentstudio-rg` | Running |
| Backend App | `curl https://<backend-fqdn>/health` | 200 OK |
| Frontend App | `curl https://<frontend-fqdn>` | 200 OK |
| Redis Connectivity | Check app logs for Redis connection | Connected |
| PostgreSQL Connectivity | Check app logs for DB queries | Connected |
| AI API Connectivity | Test workflow execution | External APIs work |

---

## Rollback Plan

If migration fails:

1. **Keep old environment running** until new one is verified
2. **Revert Front Door** to point to old FQDNs
3. **Re-enable public access** on Redis/PostgreSQL if needed:
   ```bash
   az redis update --name agentstudio-redis -g agentstudio-rg --set publicNetworkAccess=Enabled
   az postgres flexible-server update --name agentstudio-db -g agentstudio-rg --public-access Enabled
   ```
4. **Delete new resources** if needed:
   ```bash
   az containerapp env delete --name agentstudio-env-v2 -g agentstudio-rg --yes
   az network private-endpoint delete --name agentstudio-redis-pe -g agentstudio-rg
   az network private-endpoint delete --name agentstudio-postgres-pe -g agentstudio-rg
   az network nat gateway delete --name agentstudio-nat -g agentstudio-rg
   az network vnet delete --name agentstudio-vnet -g agentstudio-rg
   ```

---

## Cost Impact

| Resource | Monthly Cost (Estimate) |
|----------|------------------------|
| NAT Gateway | ~$32 + data charges |
| Private Endpoints (2) | ~$7.50 each = $15 |
| VNet | Free |
| Private DNS Zones | ~$0.50 each = $1 |
| **Total Additional** | **~$48/month** |

---

## Timeline

| Phase | Duration | Downtime |
|-------|----------|----------|
| Create VNet, Subnets, NAT | 10 mins | None |
| Create DNS Zones | 5 mins | None |
| Create Private Endpoints | 10 mins | None |
| Create New Environment | 15 mins | None |
| Migrate Container Apps | 15 mins | **Yes** |
| Update Front Door | 5 mins | Brief |
| Verification | 15 mins | None |
| Disable Public Access | 5 mins | None |
| **Total** | **~75 mins** | **~20 mins** |

---

## Security Benefits

1. **Redis** - No longer accessible from internet
2. **PostgreSQL** - No longer accessible from internet
3. **Static Outbound IP** - Predictable for allowlisting
4. **Network Isolation** - Apps run in private network
5. **Defense in Depth** - Multiple security layers

---

## Post-Migration Tasks

1. Update CI/CD pipeline to deploy to new environment
2. Update monitoring/alerting for new resources
3. Document new architecture
4. Update disaster recovery procedures
5. Review and update firewall rules if any

---

**Document Version:** 1.0
**Created:** 2026-02-08
**Author:** Claude Code
