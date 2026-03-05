# MCP Server Ecosystem Integration Plan

## Overview

Complete the MCP (Model Context Protocol) integration for AgentStudio. Most UI and backend services are already implemented - focus on the remaining gaps.

## Current State (80% Complete)

| Component | Status | Location |
|-----------|--------|----------|
| MCPService (FastMCP client) | ✅ Complete | `backend/app/services/mcp_service.py` |
| ToolType.MCP enum | ✅ Complete | `backend/app/models/tool.py` |
| MCPToolConfig schema | ✅ Complete | `backend/app/schemas/tool.py` |
| Tool test endpoint | ✅ Complete | `backend/app/api/v1/tools.py` |
| MCP Tab in Tools page | ✅ Complete | `frontend/src/pages/Tools.tsx` |
| MCP Tool Creation Modal | ✅ Complete | `frontend/src/components/Tools/ToolCreationModal.tsx` |
| MCP Tool Tester | ✅ Complete | `frontend/src/components/Tools/ToolTester.tsx` |
| MCP Tool Card display | ✅ Complete | `frontend/src/components/Tools/ToolCard.tsx` |
| _convert_mcp_tool() | **❌ TODO stub** | `backend/app/services/tool_converter.py` |
| MCP Server Registry | **❌ Missing** | - |
| Auto-discovery UI | **❌ Missing** | - |
| Credentials integration | **❌ Missing** | - |

## What's NOT Working

1. **Agents can't use MCP tools** - `_convert_mcp_tool()` is a stub
2. **No central server management** - users enter URLs per tool
3. **No auto-discovery** - users must know exact resource URIs
4. **Auth tokens in config** - not using secure Credentials system

## Remaining Work (3 Phases)

---

## Phase 1: Complete LangGraph Integration (CRITICAL)

**Goal**: Make MCP tools usable by agents during execution.

### 1.1 Implement _convert_mcp_tool()

**File**: `backend/app/services/tool_converter.py` (lines 99-109)

Current stub:
```python
@staticmethod
def _convert_mcp_tool(db_tool: Tool) -> Any:
    """Convert MCP tool to LangChain format."""
    # TODO: Implement MCP tool execution
    async def mcp_tool_func(**kwargs) -> str:
        return "MCP tool execution not yet implemented"
```

Replace with:
```python
@staticmethod
def _convert_mcp_tool(db_tool: Tool) -> StructuredTool:
    """Convert MCP tool to LangChain StructuredTool."""
    from app.services.mcp_service import mcp_service

    config = db_tool.config or {}
    server_url = config.get("mcp_server_url")
    mcp_type = config.get("mcp_type", "tool")
    resource_uri = config.get("resource_uri")

    async def mcp_execute(**kwargs) -> str:
        result = await mcp_service.execute(
            server_url=server_url,
            mcp_type=mcp_type,
            resource_uri=resource_uri,
            arguments=kwargs
        )
        return json.dumps(result.data) if result.success else result.error

    return StructuredTool.from_function(
        coroutine=mcp_execute,
        name=db_tool.name,
        description=db_tool.description,
    )
```

### 1.2 Verify LangGraph Engine Integration

**File**: `backend/app/services/langgraph_engine.py`

- Ensure MCP tools are bound to LLM agents
- Test end-to-end execution flow

---

## Phase 2: MCP Server Registry (OPTIONAL BUT RECOMMENDED)

**Goal**: Central management of MCP servers instead of per-tool URLs.

### 2.1 Create MCP Server Model

**File**: `backend/app/models/mcp_server.py`

```python
class MCPServer(Base):
    id: UUID
    organization_id: UUID
    name: str                    # "Mock Data Server"
    description: str
    server_url: str              # "https://mcp-mock.agentstudio365.com"
    transport_type: str          # "sse" | "http"
    credential_id: UUID          # FK to credentials (optional)
    status: str                  # "active" | "inactive" | "error"
    discovered_tools: JSON       # Cached list from server
    discovered_resources: JSON
    last_health_check: DateTime
```

### 2.2 Create MCP Server API

**File**: `backend/app/api/v1/mcp_servers.py`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp-servers` | GET | List servers |
| `/mcp-servers` | POST | Register server |
| `/mcp-servers/{id}` | DELETE | Remove server |
| `/mcp-servers/{id}/test` | POST | Test connection |
| `/mcp-servers/{id}/discover` | POST | Discover tools/resources |

### 2.3 Frontend: MCP Servers Page

**File**: `frontend/src/pages/MCPServers.tsx`

- List registered servers with status
- Add/Remove servers
- Test connection button
- View discovered tools/resources

### 2.4 Enhance Tool Creation Modal

**File**: `frontend/src/components/Tools/ToolCreationModal.tsx`

- Add server dropdown (select from registry)
- Auto-populate available tools from selected server
- Keep manual URL input as fallback

---

## Phase 3: Dynamic MCP Server (CREATE TOOLS VIA UI)

**Goal**: One MCP server that reads tool definitions from database. Users create tools via UI, no coding needed.

### 3.1 Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  AgentStudio UI                     Dynamic MCP Server               │
│  ┌────────────────────┐            ┌─────────────────────────────┐  │
│  │ Create API Tool:   │            │  mcp.agentstudio365.com     │  │
│  │                    │            │                             │  │
│  │ Name: get_products │── save ───▶│  Reads tool definitions     │  │
│  │ Endpoint: /products│   to DB    │  from AgentStudio DB        │  │
│  │ Method: GET        │            │                             │  │
│  │ Params: category   │            │  Dynamically exposes as     │  │
│  └────────────────────┘            │  MCP tools                  │  │
│                                    │                             │  │
│  Agent uses tool ─────────────────▶│  1. Lookup definition       │  │
│                                    │  2. Call actual API         │  │
│                                    │  3. Return result           │  │
│                                    └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Enhanced Tool Definition Schema

**File**: `backend/app/schemas/tool.py`

```python
class DynamicMCPToolConfig(BaseModel):
    """Tool definition for Dynamic MCP Server."""
    name: str                          # "get_products"
    description: str                   # "Get insurance products"
    api_endpoint: str                  # "https://insurance-api.com/products"
    method: str                        # "GET" | "POST" | "PUT" | "DELETE"
    parameters: List[ToolParameter]    # Input parameters
    headers: Optional[Dict[str, str]]  # Custom headers
    auth_type: Optional[str]           # "none" | "bearer" | "api_key"
    credential_id: Optional[UUID]      # FK to credentials
    response_mapping: Optional[Dict]   # Transform response
```

### 3.3 Dynamic MCP Server Code

**File**: `mcp-servers/dynamic-server/server.py`

```python
from fastmcp import FastMCP
import httpx

mcp = FastMCP("AgentStudio Dynamic MCP Server")

# Fetch tool definitions from AgentStudio API
async def get_tool_definitions():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{AGENTSTUDIO_API}/api/v1/mcp-tools",
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
        return response.json()

# Register tools dynamically at startup
@mcp.on_startup
async def register_dynamic_tools():
    tools = await get_tool_definitions()
    for tool_def in tools:
        register_tool_from_definition(tool_def)

def register_tool_from_definition(tool_def):
    """Create MCP tool from database definition."""

    async def dynamic_tool_handler(**kwargs):
        # Build request from definition
        url = tool_def["api_endpoint"]
        method = tool_def["method"]
        headers = build_headers(tool_def)

        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, params=kwargs, headers=headers)
            else:
                response = await client.request(method, url, json=kwargs, headers=headers)

        return response.json()

    # Register with FastMCP
    mcp.add_tool(
        name=tool_def["name"],
        description=tool_def["description"],
        handler=dynamic_tool_handler,
        parameters=tool_def["parameters"]
    )

if __name__ == "__main__":
    mcp.run(transport="sse", port=3000)
```

### 3.4 New API Endpoint for Tool Definitions

**File**: `backend/app/api/v1/mcp_tools.py`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/mcp-tools` | GET | List all MCP tool definitions (for dynamic server) |
| `/mcp-tools` | POST | Create new MCP tool definition |
| `/mcp-tools/{id}` | PATCH | Update tool definition |
| `/mcp-tools/{id}` | DELETE | Delete tool definition |
| `/mcp-tools/refresh` | POST | Trigger dynamic server to reload tools |

### 3.5 Enhanced UI: Tool Creation Modal

**File**: `frontend/src/components/Tools/ToolCreationModal.tsx`

Add new fields for API-based MCP tools:

```
┌─────────────────────────────────────────────────────────────────┐
│  Create MCP Tool                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Name:        [get_products                    ]                 │
│  Description: [Get available insurance products]                 │
│                                                                  │
│  ── API Configuration ──────────────────────────────────────    │
│                                                                  │
│  Endpoint:    [https://insurance-api.com/products]               │
│  Method:      [GET ▼]                                           │
│                                                                  │
│  ── Parameters ─────────────────────────────────────────────    │
│  │ Name     │ Type   │ Required │ Description          │        │
│  ├──────────┼────────┼──────────┼──────────────────────┤        │
│  │ category │ string │ [ ]      │ Product category     │ [×]    │
│  │ limit    │ number │ [ ]      │ Max results          │ [×]    │
│  └──────────┴────────┴──────────┴──────────────────────┘        │
│  [+ Add Parameter]                                               │
│                                                                  │
│  ── Authentication ─────────────────────────────────────────    │
│                                                                  │
│  Auth Type:   [Bearer Token ▼]                                  │
│  Credential:  [Insurance API Key ▼]                             │
│                                                                  │
│  [Test Tool]                              [Cancel] [Save]        │
└─────────────────────────────────────────────────────────────────┘
```

### 3.6 Insurance Flow Example

User creates these tools via UI:

| Tool | Endpoint | Method | Params |
|------|----------|--------|--------|
| `get_products` | `/products` | GET | category |
| `create_quote` | `/quotes` | POST | product_id, customer_data |
| `submit_quote` | `/quotes/{id}/submit` | POST | quote_id |
| `issue_policy` | `/policies` | POST | quote_id, payment_info |

All exposed automatically via `mcp.agentstudio365.com`!

### 3.7 Security Architecture

#### Problem: LLM Should NEVER See API Keys

```
❌ WRONG: LLM passes credentials
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Agent    │────▶│ MCP Server  │────▶│ External API│
│             │     │             │     │             │
│ "api_key:   │     │ Forwards    │     │             │
│  sk-xxx..." │     │ the key     │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
      ↑
      │ LLM sees and outputs secrets = SECURITY RISK!


✅ CORRECT: Credentials resolved server-side
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Agent    │────▶│ MCP Server  │────▶│ External API│
│             │     │             │     │             │
│ "tool:      │     │ 1. Lookup   │     │ Receives    │
│  get_products│    │    credential│    │ real key    │
│  category:  │     │ 2. Add auth │     │ from MCP    │
│  car"       │     │    header   │     │ server      │
└─────────────┘     └─────────────┘     └─────────────┘
      ↑                    ↑
      │                    │
      │ LLM only sees      │ Credentials stored
      │ tool name +        │ securely, fetched
      │ parameters         │ at runtime
```

#### Security Layers

**Layer 1: AgentStudio → MCP Server Authentication**

```
┌─────────────────────────────────────────────────────────────────┐
│  How AgentStudio authenticates to MCP Server                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Option A: Shared Secret (Simple)                               │
│  ┌─────────────────┐         ┌─────────────────┐                │
│  │  AgentStudio    │         │  MCP Server     │                │
│  │                 │         │                 │                │
│  │  MCP_SERVER_KEY │────────▶│  Validates key  │                │
│  │  = "secret123"  │         │  in header      │                │
│  └─────────────────┘         └─────────────────┘                │
│                                                                  │
│  Option B: JWT Token (Recommended)                              │
│  ┌─────────────────┐         ┌─────────────────┐                │
│  │  AgentStudio    │         │  MCP Server     │                │
│  │                 │         │                 │                │
│  │  Signs JWT with │────────▶│  Verifies JWT   │                │
│  │  shared secret  │         │  signature      │                │
│  │  + org_id       │         │  + org_id       │                │
│  │  + expiry       │         │  + expiry       │                │
│  └─────────────────┘         └─────────────────┘                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Layer 2: MCP Server → External API Authentication**

```
┌─────────────────────────────────────────────────────────────────┐
│  How MCP Server gets credentials for external APIs              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Tool Definition (stored in DB):                                │
│  {                                                               │
│    "name": "get_products",                                      │
│    "api_endpoint": "https://insurance-api.com/products",        │
│    "credential_id": "cred_abc123"  ◀── Reference, NOT secret    │
│  }                                                               │
│                                                                  │
│  When MCP Server executes tool:                                 │
│                                                                  │
│  1. Receive request: get_products(category="car")               │
│                           │                                      │
│                           ▼                                      │
│  2. Lookup tool definition from DB                              │
│     → Found credential_id: "cred_abc123"                        │
│                           │                                      │
│                           ▼                                      │
│  3. Fetch credential from AgentStudio API (or direct DB)       │
│     GET /api/v1/credentials/cred_abc123/decrypt                 │
│     → Returns: { "api_key": "sk-real-secret-key" }              │
│                           │                                      │
│                           ▼                                      │
│  4. Call external API with real credentials                     │
│     GET https://insurance-api.com/products?category=car         │
│     Headers: { "Authorization": "Bearer sk-real-secret-key" }   │
│                           │                                      │
│                           ▼                                      │
│  5. Return result to agent (NO secrets exposed)                 │
│     → { "products": [...] }                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Implementation Details

**1. MCP Server Environment Variables**

```bash
# MCP Server .env
AGENTSTUDIO_API_URL=https://agentstudio365.com
MCP_SERVER_SECRET=your-shared-secret-for-jwt-verification
DATABASE_URL=postgresql://...  # Read-only access to tools table
CREDENTIALS_ENCRYPTION_KEY=...  # If direct DB access to credentials
```

**2. MCP Server Authentication Middleware**

```python
# mcp-servers/dynamic-server/auth.py
from fastapi import Header, HTTPException
import jwt

async def verify_agentstudio_request(
    authorization: str = Header(...),
    x_organization_id: str = Header(...)
):
    """Verify request is from authorized AgentStudio instance."""
    try:
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, MCP_SERVER_SECRET, algorithms=["HS256"])

        if payload["org_id"] != x_organization_id:
            raise HTTPException(403, "Organization mismatch")

        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
```

**3. Credential Fetching (Two Options)**

```python
# Option A: Fetch from AgentStudio API (More Secure)
async def get_credential(credential_id: str, org_id: str) -> dict:
    """Fetch decrypted credential from AgentStudio."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{AGENTSTUDIO_API}/api/v1/internal/credentials/{credential_id}",
            headers={
                "Authorization": f"Bearer {INTERNAL_API_KEY}",
                "X-Organization-Id": org_id
            }
        )
        return response.json()  # {"api_key": "sk-xxx", "type": "bearer"}


# Option B: Direct DB Access (Faster, but MCP server needs encryption key)
async def get_credential_from_db(credential_id: str, db: AsyncSession) -> dict:
    """Fetch and decrypt credential from shared database."""
    credential = await db.get(Credential, credential_id)
    decrypted = decrypt(credential.api_key, CREDENTIALS_ENCRYPTION_KEY)
    return {"api_key": decrypted, "type": credential.auth_type}
```

**4. Secure Tool Execution Flow**

```python
# mcp-servers/dynamic-server/server.py
async def execute_tool(tool_name: str, params: dict, org_id: str) -> dict:
    """Execute tool with secure credential handling."""

    # 1. Get tool definition
    tool_def = await get_tool_definition(tool_name, org_id)

    # 2. Get credential (LLM never sees this)
    credential = None
    if tool_def.get("credential_id"):
        credential = await get_credential(tool_def["credential_id"], org_id)

    # 3. Build headers with real credentials
    headers = {"Content-Type": "application/json"}
    if credential:
        if credential["type"] == "bearer":
            headers["Authorization"] = f"Bearer {credential['api_key']}"
        elif credential["type"] == "api_key":
            headers["X-API-Key"] = credential["api_key"]

    # 4. Call external API
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=tool_def["method"],
            url=tool_def["api_endpoint"],
            headers=headers,
            params=params if tool_def["method"] == "GET" else None,
            json=params if tool_def["method"] != "GET" else None
        )

    # 5. Return result (no secrets)
    return response.json()
```

#### Runtime Token Generation

Some APIs require tokens generated at runtime (OAuth2, JWT signing, session tokens).

**Supported Auth Types:**

| Auth Type | Use Case | How It Works |
|-----------|----------|--------------|
| `static_api_key` | Simple APIs | Key stored, used directly |
| `static_bearer` | Bearer tokens | Token stored, used directly |
| `oauth2_client_credentials` | OAuth2 APIs | Generate token from client_id + client_secret |
| `oauth2_refresh_token` | OAuth2 with refresh | Exchange refresh_token for access_token |
| `jwt_signing` | JWT-based auth | Sign JWT with private key |
| `session_login` | Login-based APIs | Call login endpoint, cache session |
| `custom_script` | Complex auth | Run custom Python code |

**Credential Schema (Enhanced):**

```python
class CredentialConfig(BaseModel):
    """Stored in credentials table."""

    auth_type: str  # "static_api_key" | "oauth2_client_credentials" | etc.

    # Static credentials
    api_key: Optional[str]
    bearer_token: Optional[str]

    # OAuth2 credentials
    client_id: Optional[str]
    client_secret: Optional[str]
    token_url: Optional[str]           # e.g., "https://auth.api.com/oauth/token"
    refresh_token: Optional[str]
    scope: Optional[str]

    # JWT signing
    private_key: Optional[str]         # PEM encoded
    jwt_issuer: Optional[str]
    jwt_audience: Optional[str]
    jwt_expiry_seconds: Optional[int]  # Default 3600

    # Session login
    login_url: Optional[str]
    username: Optional[str]
    password: Optional[str]
    session_header: Optional[str]      # e.g., "X-Session-Token"

    # Custom script
    auth_script: Optional[str]         # Python code to generate token
```

**Runtime Token Generation Flow:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│  MCP Server - Token Generation                                          │
│                                                                          │
│  1. Tool request comes in                                               │
│     get_products(category="car")                                        │
│              │                                                          │
│              ▼                                                          │
│  2. Lookup credential config                                            │
│     auth_type: "oauth2_client_credentials"                              │
│     client_id: "xxx"                                                    │
│     client_secret: "yyy"                                                │
│     token_url: "https://auth.insurance.com/token"                       │
│              │                                                          │
│              ▼                                                          │
│  3. Check token cache                                                   │
│     ┌─────────────────────────────────────────────┐                     │
│     │ Redis Cache                                 │                     │
│     │ Key: "token:cred_abc123"                    │                     │
│     │ Value: {"access_token": "...", "expires": } │                     │
│     └─────────────────────────────────────────────┘                     │
│              │                                                          │
│         ┌────┴────┐                                                     │
│         │         │                                                     │
│    Cache HIT  Cache MISS/EXPIRED                                        │
│         │         │                                                     │
│         │         ▼                                                     │
│         │    4. Generate new token                                      │
│         │    POST https://auth.insurance.com/token                      │
│         │    Body: {grant_type, client_id, client_secret}               │
│         │         │                                                     │
│         │         ▼                                                     │
│         │    5. Cache token with TTL                                    │
│         │    SET token:cred_abc123 {token} EX 3500                      │
│         │         │                                                     │
│         └────┬────┘                                                     │
│              ▼                                                          │
│  6. Use token in API request                                            │
│     GET https://insurance-api.com/products                              │
│     Authorization: Bearer {generated_token}                             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Token Generator Implementation:**

```python
# mcp-servers/dynamic-server/token_generator.py
import httpx
import jwt
import time
from datetime import datetime, timedelta

class TokenGenerator:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.generators = {
            "static_api_key": self._static_api_key,
            "static_bearer": self._static_bearer,
            "oauth2_client_credentials": self._oauth2_client_credentials,
            "oauth2_refresh_token": self._oauth2_refresh_token,
            "jwt_signing": self._jwt_signing,
            "session_login": self._session_login,
        }

    async def get_auth_header(self, credential_id: str, config: dict) -> dict:
        """Get authentication header, generating token if needed."""
        auth_type = config["auth_type"]
        generator = self.generators.get(auth_type)

        if not generator:
            raise ValueError(f"Unknown auth type: {auth_type}")

        return await generator(credential_id, config)

    async def _static_api_key(self, cred_id: str, config: dict) -> dict:
        """Return static API key."""
        return {"X-API-Key": config["api_key"]}

    async def _static_bearer(self, cred_id: str, config: dict) -> dict:
        """Return static bearer token."""
        return {"Authorization": f"Bearer {config['bearer_token']}"}

    async def _oauth2_client_credentials(self, cred_id: str, config: dict) -> dict:
        """Generate OAuth2 token using client credentials flow."""
        cache_key = f"token:{cred_id}"

        # Check cache
        cached = await self.redis.get(cache_key)
        if cached:
            return {"Authorization": f"Bearer {cached}"}

        # Generate new token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                config["token_url"],
                data={
                    "grant_type": "client_credentials",
                    "client_id": config["client_id"],
                    "client_secret": config["client_secret"],
                    "scope": config.get("scope", "")
                }
            )
            token_data = response.json()

        access_token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 3600) - 60  # 1 min buffer

        # Cache token
        await self.redis.setex(cache_key, expires_in, access_token)

        return {"Authorization": f"Bearer {access_token}"}

    async def _oauth2_refresh_token(self, cred_id: str, config: dict) -> dict:
        """Generate OAuth2 token using refresh token flow."""
        cache_key = f"token:{cred_id}"

        cached = await self.redis.get(cache_key)
        if cached:
            return {"Authorization": f"Bearer {cached}"}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                config["token_url"],
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": config["refresh_token"],
                    "client_id": config["client_id"],
                    "client_secret": config.get("client_secret", "")
                }
            )
            token_data = response.json()

        access_token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 3600) - 60

        # Update refresh token if rotated
        if "refresh_token" in token_data:
            await self._update_refresh_token(cred_id, token_data["refresh_token"])

        await self.redis.setex(cache_key, expires_in, access_token)
        return {"Authorization": f"Bearer {access_token}"}

    async def _jwt_signing(self, cred_id: str, config: dict) -> dict:
        """Generate signed JWT token."""
        cache_key = f"token:{cred_id}"

        cached = await self.redis.get(cache_key)
        if cached:
            return {"Authorization": f"Bearer {cached}"}

        expiry = config.get("jwt_expiry_seconds", 3600)
        payload = {
            "iss": config["jwt_issuer"],
            "aud": config["jwt_audience"],
            "iat": int(time.time()),
            "exp": int(time.time()) + expiry
        }

        token = jwt.encode(payload, config["private_key"], algorithm="RS256")

        await self.redis.setex(cache_key, expiry - 60, token)
        return {"Authorization": f"Bearer {token}"}

    async def _session_login(self, cred_id: str, config: dict) -> dict:
        """Login and get session token."""
        cache_key = f"token:{cred_id}"

        cached = await self.redis.get(cache_key)
        if cached:
            return {config.get("session_header", "X-Session-Token"): cached}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                config["login_url"],
                json={
                    "username": config["username"],
                    "password": config["password"]
                }
            )
            session_data = response.json()

        session_token = session_data.get("token") or session_data.get("session_token")
        expires_in = session_data.get("expires_in", 3600) - 60

        await self.redis.setex(cache_key, expires_in, session_token)
        return {config.get("session_header", "X-Session-Token"): session_token}
```

**UI Enhancement for Credential Creation:**

```
┌─────────────────────────────────────────────────────────────────┐
│  Create Credential                                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Name:      [Insurance API OAuth            ]                    │
│                                                                  │
│  Auth Type: [OAuth2 Client Credentials ▼]                       │
│             ├─ Static API Key                                    │
│             ├─ Static Bearer Token                               │
│             ├─ OAuth2 Client Credentials  ◀── Selected          │
│             ├─ OAuth2 Refresh Token                              │
│             ├─ JWT Signing                                       │
│             └─ Session Login                                     │
│                                                                  │
│  ── OAuth2 Settings ───────────────────────────────────────     │
│                                                                  │
│  Token URL:     [https://auth.insurance.com/oauth/token]        │
│  Client ID:     [my-client-id                          ]        │
│  Client Secret: [••••••••••••••••••                    ]        │
│  Scope:         [read:products write:quotes            ]        │
│                                                                  │
│  [Test Connection]                          [Cancel] [Save]      │
└─────────────────────────────────────────────────────────────────┘
```

#### Security Summary

| Layer | Protection | Implementation |
|-------|------------|----------------|
| **AgentStudio → MCP** | JWT or API Key | MCP server validates token |
| **MCP → External APIs** | Credential lookup | credential_id in tool def, resolved at runtime |
| **Runtime tokens** | Token generator | OAuth2, JWT signing, session login |
| **Token caching** | Redis with TTL | Avoid regenerating on every request |
| **LLM isolation** | Never sees secrets | Only tool name + params passed to LLM |
| **Credential storage** | Encrypted in DB | AES-256 encryption in credentials table |
| **Network** | HTTPS only | TLS for all communications |
| **Organization isolation** | Org ID validation | Tools/credentials scoped to organization |

#### New API Endpoint Needed

**File**: `backend/app/api/v1/credentials.py`

Add internal endpoint for MCP server:

```python
@router.get("/internal/credentials/{credential_id}")
async def get_credential_internal(
    credential_id: UUID,
    x_internal_key: str = Header(...),
    x_organization_id: str = Header(...),
    db: AsyncSession = Depends(get_db)
):
    """Internal endpoint for MCP server to fetch decrypted credentials."""
    # Verify internal API key
    if x_internal_key != settings.MCP_INTERNAL_API_KEY:
        raise HTTPException(403, "Invalid internal key")

    credential = await db.get(Credential, credential_id)
    if not credential or str(credential.organization_id) != x_organization_id:
        raise HTTPException(404, "Credential not found")

    return {
        "api_key": decrypt_credential(credential.api_key),
        "type": credential.auth_type,
        "api_base": credential.api_base
    }
```

### 3.8 Azure Deployment

**Single deployment** for Dynamic MCP Server:

```yaml
# Azure Container App
name: dynamic-mcp-server
image: agentstudio/dynamic-mcp:latest
ingress:
  external: true
  targetPort: 3000
  customDomains:
    - mcp.agentstudio365.com
env:
  - name: AGENTSTUDIO_API_URL
    value: https://agentstudio365.com
  - name: MCP_SERVER_SECRET
    secretRef: mcp-server-secret
  - name: MCP_INTERNAL_API_KEY
    secretRef: mcp-internal-api-key
  - name: DATABASE_URL
    secretRef: database-url
```

---

## Implementation Order

| Step | Task | File | Priority |
|------|------|------|----------|
| **1** | Implement `_convert_mcp_tool()` | `backend/app/services/tool_converter.py` | **CRITICAL** |
| **2** | Test MCP tool in agent execution | `backend/app/services/langgraph_engine.py` | **CRITICAL** |
| 3 | Create MCP Server registry model | `backend/app/models/mcp_server.py` | Medium |
| 4 | Create MCP Server API | `backend/app/api/v1/mcp_servers.py` | Medium |
| 5 | Database migration | `backend/alembic/versions/004_*.py` | Medium |
| 6 | Frontend: MCP Servers page | `frontend/src/pages/MCPServers.tsx` | Medium |
| **7** | Enhanced Tool schema (API config) | `backend/app/schemas/tool.py` | **HIGH** |
| **8** | MCP Tools API endpoint | `backend/app/api/v1/mcp_tools.py` | **HIGH** |
| **9** | Enhance Tool Creation Modal | `frontend/src/components/Tools/ToolCreationModal.tsx` | **HIGH** |
| **10** | Create Dynamic MCP Server | `mcp-servers/dynamic-server/` | **HIGH** |
| 11 | Deploy to Azure | Azure Container Apps | Medium |

---

## Quick Start (Minimum Viable)

To get MCP tools working in agents immediately, only **Step 1** is required:

```
Fix _convert_mcp_tool() in tool_converter.py
    ↓
MCP tools created via existing UI will work in agents
    ↓
Users can connect to any MCP server URL
```

The MCP Server Registry (Steps 3-6) is optional but improves UX.

---

## Key Files

### Phase 1 - Must Modify
- `backend/app/services/tool_converter.py` - Lines 99-109 (the TODO stub)
- `backend/app/services/langgraph_engine.py` - MCP tool binding verification

### Phase 2 - New Files
- `backend/app/models/mcp_server.py` - Server registry model
- `backend/app/api/v1/mcp_servers.py` - Server management API
- `frontend/src/pages/MCPServers.tsx` - Server management UI

### Phase 3 - Dynamic MCP Server
- `backend/app/schemas/tool.py` - Add DynamicMCPToolConfig
- `backend/app/api/v1/mcp_tools.py` - Tool definitions API
- `frontend/src/components/Tools/ToolCreationModal.tsx` - Enhanced UI
- `mcp-servers/dynamic-server/server.py` - The dynamic server
- `mcp-servers/dynamic-server/Dockerfile` - Container config

---

## Success Criteria

1. ✅ MCP tools can be created via existing UI (already works)
2. ✅ MCP tools can be tested via existing tester (already works)
3. **❌ Agents can use MCP tools during execution** (needs Phase 1)
4. ❌ MCP servers can be managed centrally (Phase 2)
5. **❌ Users can create MCP tools via UI without coding** (Phase 3)
6. ❌ Insurance flow tools work end-to-end (Phase 3 example)
