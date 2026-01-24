# Azure Front Door Setup Guide

This guide covers setting up Azure Front Door as a load balancer/reverse proxy for AgentStudio with the custom domain `agentstudio365.com`.

## Architecture Overview

```
                         ┌──────────────────────────────┐
                         │     agentstudio365.com       │
                         │     (Azure Front Door)       │
                         │                              │
                         │  - SSL Termination           │
                         │  - WAF Protection            │
                         │  - Global CDN                │
                         │  - Path-based Routing        │
                         └──────────────┬───────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
                    ▼                   ▼                   ▼
              /api/v1/*            /api/*              /* (default)
                    │                   │                   │
                    ▼                   ▼                   ▼
         ┌─────────────────────────────────┐    ┌─────────────────────┐
         │       Backend Container App      │    │  Frontend Container │
         │  (agentstudio-backend)           │    │  (agentstudio-frontend)
         └─────────────────────────────────┘    └─────────────────────┘
```

## Routing Rules

| URL Pattern | Destination | Description |
|-------------|-------------|-------------|
| `agentstudio365.com/api/*` | Backend Container App | All API requests |
| `agentstudio365.com/*` | Frontend Container App | Frontend application (default) |

## Prerequisites

- Azure CLI installed and logged in
- Resource Group: `agentstudio-rg`
- Existing Container Apps:
  - Backend: `agentstudio-backend.orangestone-66d8b5ee.uaenorth.azurecontainerapps.io`
  - Frontend: `agentstudio-frontend.orangestone-66d8b5ee.uaenorth.azurecontainerapps.io`
- Domain: `agentstudio365.com` with DNS access

---

## Step 1: Create Azure Front Door Profile

```bash
# Create Front Door profile (Standard tier)
az afd profile create \
  --profile-name agentstudio-fd \
  --resource-group agentstudio-rg \
  --sku Standard_AzureFrontDoor
```

## Step 2: Create Front Door Endpoint

```bash
# Create endpoint (this generates a temporary URL like agentstudio-xxxxx.z01.azurefd.net)
az afd endpoint create \
  --endpoint-name agentstudio \
  --profile-name agentstudio-fd \
  --resource-group agentstudio-rg \
  --enabled-state Enabled
```

## Step 3: Create Backend Origin Group

```bash
# Create origin group for Backend API
az afd origin-group create \
  --origin-group-name backend-origin-group \
  --profile-name agentstudio-fd \
  --resource-group agentstudio-rg \
  --probe-request-type GET \
  --probe-protocol Https \
  --probe-path /health \
  --probe-interval-in-seconds 30 \
  --sample-size 4 \
  --successful-samples-required 3
```

## Step 4: Add Backend Origin

```bash
# Add Backend Container App as origin
az afd origin create \
  --origin-name backend-origin \
  --origin-group-name backend-origin-group \
  --profile-name agentstudio-fd \
  --resource-group agentstudio-rg \
  --host-name agentstudio-backend.orangestone-66d8b5ee.uaenorth.azurecontainerapps.io \
  --origin-host-header agentstudio-backend.orangestone-66d8b5ee.uaenorth.azurecontainerapps.io \
  --http-port 80 \
  --https-port 443 \
  --priority 1 \
  --weight 1000 \
  --enabled-state Enabled
```

## Step 5: Create Frontend Origin Group

```bash
# Create origin group for Frontend
az afd origin-group create \
  --origin-group-name frontend-origin-group \
  --profile-name agentstudio-fd \
  --resource-group agentstudio-rg \
  --probe-request-type GET \
  --probe-protocol Https \
  --probe-path / \
  --probe-interval-in-seconds 30 \
  --sample-size 4 \
  --successful-samples-required 3
```

## Step 6: Add Frontend Origin

```bash
# Add Frontend Container App as origin
az afd origin create \
  --origin-name frontend-origin \
  --origin-group-name frontend-origin-group \
  --profile-name agentstudio-fd \
  --resource-group agentstudio-rg \
  --host-name agentstudio-frontend.orangestone-66d8b5ee.uaenorth.azurecontainerapps.io \
  --origin-host-header agentstudio-frontend.orangestone-66d8b5ee.uaenorth.azurecontainerapps.io \
  --http-port 80 \
  --https-port 443 \
  --priority 1 \
  --weight 1000 \
  --enabled-state Enabled
```

## Step 7: Create API Route (Backend)

```bash
# Route /api/* to Backend
az afd route create \
  --route-name api-route \
  --endpoint-name agentstudio \
  --profile-name agentstudio-fd \
  --resource-group agentstudio-rg \
  --origin-group backend-origin-group \
  --patterns "/api/*" \
  --supported-protocols Https \
  --https-redirect Enabled \
  --forwarding-protocol HttpsOnly \
  --link-to-default-domain Enabled
```

## Step 8: Create Frontend Route (Default)

```bash
# Route everything else to Frontend
az afd route create \
  --route-name frontend-route \
  --endpoint-name agentstudio \
  --profile-name agentstudio-fd \
  --resource-group agentstudio-rg \
  --origin-group frontend-origin-group \
  --patterns "/*" \
  --supported-protocols Https \
  --https-redirect Enabled \
  --forwarding-protocol HttpsOnly \
  --link-to-default-domain Enabled
```

---

## Step 9: Configure Custom Domain

### 9.1 Add Custom Domain to Front Door

```bash
# Add agentstudio365.com as custom domain
az afd custom-domain create \
  --custom-domain-name agentstudio365 \
  --profile-name agentstudio-fd \
  --resource-group agentstudio-rg \
  --host-name agentstudio365.com \
  --certificate-type ManagedCertificate \
  --minimum-tls-version TLS12
```

### 9.2 DNS Configuration

Add the following DNS records at your domain registrar:

#### For Root Domain (agentstudio365.com)

| Type | Name | Value |
|------|------|-------|
| CNAME | `_dnsauth` | `<validation-token>.agentstudio365.com.dnsauth.azurefd.net` |
| ALIAS/ANAME | `@` | `agentstudio-<hash>.z01.azurefd.net` |

> **Note:** The validation token will be provided after running the custom-domain create command. Check Azure Portal for the exact value.

#### Alternative: Using www subdomain

| Type | Name | Value |
|------|------|-------|
| CNAME | `www` | `agentstudio-<hash>.z01.azurefd.net` |
| CNAME | `_dnsauth.www` | `<validation-token>.www.agentstudio365.com.dnsauth.azurefd.net` |

### 9.3 Associate Custom Domain with Routes

```bash
# Associate with API route
az afd route update \
  --route-name api-route \
  --endpoint-name agentstudio \
  --profile-name agentstudio-fd \
  --resource-group agentstudio-rg \
  --custom-domains agentstudio365

# Associate with Frontend route
az afd route update \
  --route-name frontend-route \
  --endpoint-name agentstudio \
  --profile-name agentstudio-fd \
  --resource-group agentstudio-rg \
  --custom-domains agentstudio365
```

---

## Step 10: Application Configuration Changes

This section covers all application-side changes required for the custom domain.

### 10.1 GitHub Secrets (CI/CD)

Update the following secret in GitHub Repository Settings → Secrets and Variables → Actions:

| Secret | Current Value | New Value |
|--------|---------------|-----------|
| `API_BASE_URL` | `https://agentstudio-backend.orangestone-66d8b5ee.uaenorth.azurecontainerapps.io` | `https://agentstudio365.com` |

### 10.2 Azure Environment Variables (Runtime)

#### Backend Container App
```bash
az containerapp update \
  --name agentstudio-backend \
  --resource-group agentstudio-rg \
  --set-env-vars \
    "API_BASE_URL=https://agentstudio365.com/api/v1" \
    "CORS_ORIGINS=[\"https://agentstudio365.com\",\"https://www.agentstudio365.com\"]"
```

#### Frontend Container App
```bash
# Note: Frontend is built with VITE_API_BASE_URL baked in during Docker build
# Updating env var here won't work - need to rebuild via GitHub Actions
# After updating GitHub secret, trigger a new deployment
```

### 10.3 Code Changes Required

The following files need to be updated in the codebase:

#### File: `backend/app/core/config.py`

**Change:** Add production domain to default CORS origins

```python
# Line 42 - Add agentstudio365.com to CORS_ORIGINS
CORS_ORIGINS: List[str] = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "https://agentstudio365.com"
]
```

#### File: `backend/.env.example`

**Change:** Document production CORS configuration

```bash
# Update CORS_ORIGINS example
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000","https://agentstudio365.com"]
```

#### File: `frontend/.env.example`

**Change:** Document production API URL

```bash
# Add production example
VITE_API_BASE_URL=http://localhost:8000
# Production: https://agentstudio365.com
```

#### File: `frontend/src/components/Testing/AgentPlayground.tsx`

**Change:** Remove hardcoded localhost reference (Line 358)

```typescript
// FROM:
errorMsg = 'Cannot connect to backend server. Please ensure the backend is running on http://localhost:8000';

// TO:
errorMsg = 'Cannot connect to backend server. Please check your network connection.';
```

### 10.4 Summary of Changes

| Component | Location | Change | Priority |
|-----------|----------|--------|----------|
| GitHub Secret | Repository Settings | Update `API_BASE_URL` | **Required** |
| Backend Env | Azure Container App | Update `API_BASE_URL`, `CORS_ORIGINS` | **Required** |
| Backend Code | `config.py:42` | Add domain to CORS defaults | Recommended |
| Backend Docs | `.env.example` | Document production config | Recommended |
| Frontend Docs | `.env.example` | Document production URL | Recommended |
| Frontend Code | `AgentPlayground.tsx:358` | Remove hardcoded URL | Recommended |

### 10.5 Deployment Order

1. Make code changes and commit to repository
2. Update GitHub Secret (`API_BASE_URL=https://agentstudio365.com`)
3. Set up Azure Front Door (Steps 1-9)
4. Configure DNS records
5. Update Backend Azure env vars (CORS, API_BASE_URL)
6. Trigger GitHub Actions to rebuild frontend with new API URL
7. Verify SSL certificate is active
8. Test all endpoints

---

## Step 11: Optional - Enable WAF (Web Application Firewall)

```bash
# Create WAF policy
az network front-door waf-policy create \
  --name agentstudio-waf \
  --resource-group agentstudio-rg \
  --sku Standard_AzureFrontDoor \
  --mode Prevention

# Associate WAF with Front Door
az afd security-policy create \
  --security-policy-name agentstudio-security \
  --profile-name agentstudio-fd \
  --resource-group agentstudio-rg \
  --waf-policy /subscriptions/<subscription-id>/resourceGroups/agentstudio-rg/providers/Microsoft.Network/FrontDoorWebApplicationFirewallPolicies/agentstudio-waf \
  --domains agentstudio365
```

---

## Verification

### Check Front Door Status

```bash
# List endpoints
az afd endpoint list \
  --profile-name agentstudio-fd \
  --resource-group agentstudio-rg \
  --output table

# Check custom domain status
az afd custom-domain show \
  --custom-domain-name agentstudio365 \
  --profile-name agentstudio-fd \
  --resource-group agentstudio-rg
```

### Test Endpoints

```bash
# Test Frontend
curl -I https://agentstudio365.com/

# Test Backend API
curl https://agentstudio365.com/api/v1/health

# Test Public Deployment Endpoint
curl https://agentstudio365.com/api/v1/orgs/agentstudio/deployments/<deployment-id>/health
```

---

## Troubleshooting

### Certificate Validation Pending

If certificate validation is stuck:
1. Verify DNS CNAME records are correctly set
2. Wait up to 24 hours for DNS propagation
3. Check Azure Portal > Front Door > Custom Domains for validation status

### 404 Errors on API Routes

1. Verify route patterns are correct (`/api/*`)
2. Check origin health in Azure Portal
3. Ensure backend health endpoint returns 200

### CORS Errors

1. Verify `CORS_ORIGINS` includes the Front Door domain
2. Check browser console for specific CORS error messages
3. Restart backend container after updating environment variables

---

## Cost Estimation

| Component | Tier | Estimated Cost (USD/month) |
|-----------|------|---------------------------|
| Azure Front Door | Standard | ~$35 base + $0.01/GB data transfer |
| Managed SSL Certificate | Included | $0 |
| WAF (Optional) | Standard | ~$5/month + $1/million requests |

---

## Related Documentation

- [Azure Front Door Documentation](https://docs.microsoft.com/en-us/azure/frontdoor/)
- [Custom Domains in Azure Front Door](https://docs.microsoft.com/en-us/azure/frontdoor/front-door-custom-domain)
- [Azure Container Apps Networking](https://docs.microsoft.com/en-us/azure/container-apps/networking)

---

## Quick Reference - All Commands

```bash
# ============================================
# COMPLETE SETUP SCRIPT FOR agentstudio365.com
# ============================================

# Variables
RESOURCE_GROUP="agentstudio-rg"
PROFILE_NAME="agentstudio-fd"
ENDPOINT_NAME="agentstudio"
DOMAIN="agentstudio365.com"
BACKEND_HOST="agentstudio-backend.orangestone-66d8b5ee.uaenorth.azurecontainerapps.io"
FRONTEND_HOST="agentstudio-frontend.orangestone-66d8b5ee.uaenorth.azurecontainerapps.io"

# 1. Create Front Door Profile
az afd profile create \
  --profile-name $PROFILE_NAME \
  --resource-group $RESOURCE_GROUP \
  --sku Standard_AzureFrontDoor

# 2. Create Endpoint
az afd endpoint create \
  --endpoint-name $ENDPOINT_NAME \
  --profile-name $PROFILE_NAME \
  --resource-group $RESOURCE_GROUP \
  --enabled-state Enabled

# 3. Backend Origin Group
az afd origin-group create \
  --origin-group-name backend-origin-group \
  --profile-name $PROFILE_NAME \
  --resource-group $RESOURCE_GROUP \
  --probe-request-type GET \
  --probe-protocol Https \
  --probe-path /health

# 4. Backend Origin
az afd origin create \
  --origin-name backend-origin \
  --origin-group-name backend-origin-group \
  --profile-name $PROFILE_NAME \
  --resource-group $RESOURCE_GROUP \
  --host-name $BACKEND_HOST \
  --origin-host-header $BACKEND_HOST \
  --https-port 443 \
  --priority 1

# 5. Frontend Origin Group
az afd origin-group create \
  --origin-group-name frontend-origin-group \
  --profile-name $PROFILE_NAME \
  --resource-group $RESOURCE_GROUP \
  --probe-request-type GET \
  --probe-protocol Https \
  --probe-path /

# 6. Frontend Origin
az afd origin create \
  --origin-name frontend-origin \
  --origin-group-name frontend-origin-group \
  --profile-name $PROFILE_NAME \
  --resource-group $RESOURCE_GROUP \
  --host-name $FRONTEND_HOST \
  --origin-host-header $FRONTEND_HOST \
  --https-port 443 \
  --priority 1

# 7. API Route
az afd route create \
  --route-name api-route \
  --endpoint-name $ENDPOINT_NAME \
  --profile-name $PROFILE_NAME \
  --resource-group $RESOURCE_GROUP \
  --origin-group backend-origin-group \
  --patterns "/api/*" \
  --supported-protocols Https \
  --https-redirect Enabled \
  --forwarding-protocol HttpsOnly \
  --link-to-default-domain Enabled

# 8. Frontend Route
az afd route create \
  --route-name frontend-route \
  --endpoint-name $ENDPOINT_NAME \
  --profile-name $PROFILE_NAME \
  --resource-group $RESOURCE_GROUP \
  --origin-group frontend-origin-group \
  --patterns "/*" \
  --supported-protocols Https \
  --https-redirect Enabled \
  --forwarding-protocol HttpsOnly \
  --link-to-default-domain Enabled

# 9. Custom Domain
az afd custom-domain create \
  --custom-domain-name agentstudio365 \
  --profile-name $PROFILE_NAME \
  --resource-group $RESOURCE_GROUP \
  --host-name $DOMAIN \
  --certificate-type ManagedCertificate

# 10. Update Backend Config
az containerapp update \
  --name agentstudio-backend \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars \
    "API_BASE_URL=https://$DOMAIN/api/v1" \
    "CORS_ORIGINS=[\"https://$DOMAIN\"]"

# 11. Update Frontend Config
az containerapp update \
  --name agentstudio-frontend \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars \
    "VITE_API_BASE_URL=https://$DOMAIN"

echo "Setup complete! Configure DNS records and wait for certificate validation."
```

---

**Last Updated:** 2026-01-23
**Domain:** agentstudio365.com
