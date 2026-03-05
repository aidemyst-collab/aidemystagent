# MCP Ecosystem - Developer Tasks

> Generated from MCP_ECOSYSTEM_PLAN.md
> Total Phases: 3 | Total Tasks: 42 | Estimated Effort: ~2-3 sprints

---

## Overview

| Phase | Description | Priority | Tasks |
|-------|-------------|----------|-------|
| **Phase 1** | LangGraph Integration | CRITICAL | 5 |
| **Phase 2** | MCP Server Registry | Medium | 12 |
| **Phase 3** | Dynamic MCP Server | HIGH | 25 |

---

## Phase 1: LangGraph Integration (CRITICAL)

> **Goal**: Enable agents to use MCP tools during execution
> **Effort**: 1-2 days
> **Blocker**: Everything else depends on this

### Backend Tasks

#### P1-001: Implement _convert_mcp_tool()
- **File**: `backend/app/services/tool_converter.py`
- **Lines**: 99-109
- **Complexity**: Medium
- **Dependencies**: None
- **Description**: Replace TODO stub with actual implementation that converts MCP tool to LangChain StructuredTool
- **Acceptance Criteria**:
  - [ ] MCP tool config is extracted (server_url, mcp_type, resource_uri)
  - [ ] Async function calls mcp_service.execute()
  - [ ] Returns StructuredTool compatible with LangGraph
  - [ ] Handles errors gracefully

```python
# Target implementation
@staticmethod
def _convert_mcp_tool(db_tool: Tool) -> StructuredTool:
    from app.services.mcp_service import mcp_service
    config = db_tool.config or {}
    # ... implementation
```

---

#### P1-002: Verify MCP tool binding in LangGraph Engine
- **File**: `backend/app/services/langgraph_engine.py`
- **Complexity**: Low
- **Dependencies**: P1-001
- **Description**: Ensure MCP tools are properly bound to LLM agents during graph construction
- **Acceptance Criteria**:
  - [ ] MCP tools appear in tool list for LLM_AGENT nodes
  - [ ] Tool execution routes correctly to MCP service
  - [ ] Tool results are returned to agent state

---

#### P1-003: Add MCP tool execution logging
- **File**: `backend/app/services/mcp_service.py`
- **Complexity**: Low
- **Dependencies**: P1-001
- **Description**: Add structured logging for MCP tool calls for debugging
- **Acceptance Criteria**:
  - [ ] Log tool name, server URL, parameters
  - [ ] Log response time and status
  - [ ] Log errors with context

---

#### P1-004: Write unit tests for _convert_mcp_tool
- **File**: `backend/tests/services/test_tool_converter.py` (new)
- **Complexity**: Medium
- **Dependencies**: P1-001
- **Description**: Unit tests for MCP tool conversion
- **Acceptance Criteria**:
  - [ ] Test with valid MCP tool config
  - [ ] Test with missing config fields
  - [ ] Test error handling
  - [ ] Mock mcp_service for isolation

---

#### P1-005: Integration test - Agent with MCP tool
- **File**: `backend/tests/integration/test_mcp_agent.py` (new)
- **Complexity**: Medium
- **Dependencies**: P1-001, P1-002
- **Description**: End-to-end test of agent using MCP tool
- **Acceptance Criteria**:
  - [ ] Create test agent with MCP tool
  - [ ] Execute agent with user query
  - [ ] Verify MCP tool is called
  - [ ] Verify response includes tool result

---

## Phase 2: MCP Server Registry (Medium Priority)

> **Goal**: Central management of MCP servers
> **Effort**: 3-4 days
> **Dependencies**: Phase 1 complete

### Backend Tasks

#### P2-001: Create MCPServer model
- **File**: `backend/app/models/mcp_server.py` (new)
- **Complexity**: Low
- **Dependencies**: None
- **Description**: SQLAlchemy model for MCP server registry
- **Fields**:
  - id (UUID)
  - organization_id (FK)
  - name, description
  - server_url
  - transport_type (sse/http)
  - credential_id (FK, optional)
  - status (active/inactive/error)
  - discovered_tools (JSON)
  - discovered_resources (JSON)
  - last_health_check (DateTime)
  - created_at, updated_at

---

#### P2-002: Create MCPServer schemas
- **File**: `backend/app/schemas/mcp_server.py` (new)
- **Complexity**: Low
- **Dependencies**: P2-001
- **Description**: Pydantic schemas for MCP server CRUD
- **Schemas**:
  - MCPServerCreate
  - MCPServerUpdate
  - MCPServerResponse
  - MCPServerDiscovery

---

#### P2-003: Database migration for mcp_servers table
- **File**: `backend/alembic/versions/004_add_mcp_servers.py` (new)
- **Complexity**: Low
- **Dependencies**: P2-001
- **Description**: Alembic migration to create mcp_servers table
- **Acceptance Criteria**:
  - [ ] Table created with all fields
  - [ ] Foreign keys to organizations and credentials
  - [ ] Indexes on organization_id and status

---

#### P2-004: Create MCP Servers API endpoints
- **File**: `backend/app/api/v1/mcp_servers.py` (new)
- **Complexity**: Medium
- **Dependencies**: P2-001, P2-002
- **Endpoints**:
  - [ ] GET /mcp-servers - List servers (filtered by org)
  - [ ] POST /mcp-servers - Register new server
  - [ ] GET /mcp-servers/{id} - Get server details
  - [ ] PATCH /mcp-servers/{id} - Update server
  - [ ] DELETE /mcp-servers/{id} - Remove server
  - [ ] POST /mcp-servers/{id}/test - Test connection
  - [ ] POST /mcp-servers/{id}/discover - Discover tools/resources
  - [ ] GET /mcp-servers/{id}/health - Health check

---

#### P2-005: Register MCP servers router
- **File**: `backend/app/main.py`
- **Complexity**: Low
- **Dependencies**: P2-004
- **Description**: Add mcp_servers router to FastAPI app
- **Acceptance Criteria**:
  - [ ] Router included in app
  - [ ] Endpoints accessible at /api/v1/mcp-servers

---

#### P2-006: Implement server discovery service
- **File**: `backend/app/services/mcp_discovery.py` (new)
- **Complexity**: Medium
- **Dependencies**: P2-004
- **Description**: Service to discover tools/resources from MCP server
- **Acceptance Criteria**:
  - [ ] Call MCP server's list_tools endpoint
  - [ ] Call MCP server's list_resources endpoint
  - [ ] Cache results in mcp_servers.discovered_tools
  - [ ] Handle connection errors

---

### Frontend Tasks

#### P2-007: Create MCP Servers service
- **File**: `frontend/src/features/mcp-servers/mcpServerService.ts` (new)
- **Complexity**: Low
- **Dependencies**: P2-004
- **Description**: API service for MCP server management
- **Methods**:
  - getServers()
  - createServer()
  - updateServer()
  - deleteServer()
  - testConnection()
  - discoverTools()

---

#### P2-008: Create MCP Servers page
- **File**: `frontend/src/pages/MCPServers.tsx` (new)
- **Complexity**: Medium
- **Dependencies**: P2-007
- **Description**: Page to list and manage MCP servers
- **Components**:
  - [ ] Server list with cards
  - [ ] Status indicators (active/error)
  - [ ] Add server button
  - [ ] Test connection button
  - [ ] Discover tools button
  - [ ] Delete confirmation

---

#### P2-009: Create MCP Server modal
- **File**: `frontend/src/components/MCPServers/MCPServerModal.tsx` (new)
- **Complexity**: Medium
- **Dependencies**: P2-008
- **Description**: Modal for adding/editing MCP servers
- **Fields**:
  - [ ] Name
  - [ ] Description
  - [ ] Server URL
  - [ ] Transport type (SSE/HTTP)
  - [ ] Credential dropdown (optional)
  - [ ] Test connection button

---

#### P2-010: Create MCP Server card component
- **File**: `frontend/src/components/MCPServers/MCPServerCard.tsx` (new)
- **Complexity**: Low
- **Dependencies**: P2-008
- **Description**: Card component for displaying MCP server
- **Features**:
  - [ ] Name and description
  - [ ] Status badge
  - [ ] Last health check time
  - [ ] Discovered tools count
  - [ ] Action buttons

---

#### P2-011: Add MCP Servers to navigation
- **File**: `frontend/src/components/Common/Layout.tsx`
- **Complexity**: Low
- **Dependencies**: P2-008
- **Description**: Add "MCP Servers" to sidebar navigation
- **Acceptance Criteria**:
  - [ ] Menu item appears under Tools section
  - [ ] Icon appropriate (server/cloud icon)
  - [ ] Links to /mcp-servers route

---

#### P2-012: Add MCP Servers route
- **File**: `frontend/src/App.tsx`
- **Complexity**: Low
- **Dependencies**: P2-008
- **Description**: Add route for MCP Servers page
- **Acceptance Criteria**:
  - [ ] Route /mcp-servers renders MCPServers page
  - [ ] Protected route (requires auth)

---

## Phase 3: Dynamic MCP Server (HIGH Priority)

> **Goal**: Create tools via UI, no coding needed
> **Effort**: 5-7 days
> **Dependencies**: Phase 1 complete (Phase 2 optional)

### Backend Tasks - Schema & API

#### P3-001: Create DynamicMCPToolConfig schema
- **File**: `backend/app/schemas/tool.py`
- **Complexity**: Medium
- **Dependencies**: None
- **Description**: Enhanced schema for API-based MCP tools
- **Fields**:
  - name, description
  - api_endpoint
  - method (GET/POST/PUT/DELETE)
  - parameters (List[ToolParameter])
  - headers (optional)
  - credential_id (optional)
  - response_mapping (optional)

---

#### P3-002: Create MCP Tools API endpoint
- **File**: `backend/app/api/v1/mcp_tools.py` (new)
- **Complexity**: Medium
- **Dependencies**: P3-001
- **Endpoints**:
  - [ ] GET /mcp-tools - List tool definitions (for dynamic server)
  - [ ] POST /mcp-tools - Create tool definition
  - [ ] PATCH /mcp-tools/{id} - Update tool
  - [ ] DELETE /mcp-tools/{id} - Delete tool
  - [ ] POST /mcp-tools/refresh - Notify server to reload

---

#### P3-003: Register MCP tools router
- **File**: `backend/app/main.py`
- **Complexity**: Low
- **Dependencies**: P3-002
- **Description**: Add mcp_tools router

---

### Backend Tasks - Security & Credentials

#### P3-004: Create CredentialConfig schema (enhanced)
- **File**: `backend/app/schemas/credential.py`
- **Complexity**: Medium
- **Dependencies**: None
- **Description**: Enhanced credential schema for runtime token generation
- **Auth Types**:
  - static_api_key
  - static_bearer
  - oauth2_client_credentials
  - oauth2_refresh_token
  - jwt_signing
  - session_login

---

#### P3-005: Create internal credentials endpoint
- **File**: `backend/app/api/v1/credentials.py`
- **Complexity**: Medium
- **Dependencies**: P3-004
- **Description**: Internal endpoint for MCP server to fetch decrypted credentials
- **Endpoint**: GET /internal/credentials/{id}
- **Security**:
  - [ ] Verify X-Internal-Key header
  - [ ] Verify X-Organization-Id header
  - [ ] Return decrypted credential

---

#### P3-006: Update credentials table migration
- **File**: `backend/alembic/versions/005_enhance_credentials.py` (new)
- **Complexity**: Medium
- **Dependencies**: P3-004
- **Description**: Add new fields for OAuth2, JWT signing, etc.
- **New Columns**:
  - auth_type
  - client_id, client_secret
  - token_url, refresh_token, scope
  - private_key, jwt_issuer, jwt_audience
  - login_url, username, password

---

### Frontend Tasks - Enhanced UI

#### P3-007: Enhance Tool Creation Modal - API Config
- **File**: `frontend/src/components/Tools/ToolCreationModal.tsx`
- **Complexity**: High
- **Dependencies**: P3-001, P3-002
- **Description**: Add API configuration fields for MCP tools
- **New Fields**:
  - [ ] API Endpoint URL input
  - [ ] HTTP Method dropdown (GET/POST/PUT/DELETE)
  - [ ] Parameters table (add/remove rows)
  - [ ] Headers table (optional)
  - [ ] Credential dropdown
  - [ ] Test API button

---

#### P3-008: Create ParametersEditor component
- **File**: `frontend/src/components/Tools/ParametersEditor.tsx` (new)
- **Complexity**: Medium
- **Dependencies**: P3-007
- **Description**: Reusable component for editing tool parameters
- **Features**:
  - [ ] Add/remove parameters
  - [ ] Name, type, required, description fields
  - [ ] Drag to reorder
  - [ ] Validation

---

#### P3-009: Enhance Credentials Modal - Auth Types
- **File**: `frontend/src/components/Credentials/CredentialModal.tsx`
- **Complexity**: High
- **Dependencies**: P3-004
- **Description**: Add support for different auth types
- **Auth Type Sections**:
  - [ ] Static API Key - just key field
  - [ ] Static Bearer - just token field
  - [ ] OAuth2 Client Credentials - token_url, client_id, client_secret, scope
  - [ ] OAuth2 Refresh Token - above + refresh_token
  - [ ] JWT Signing - private_key, issuer, audience, expiry
  - [ ] Session Login - login_url, username, password

---

#### P3-010: Update credentials service
- **File**: `frontend/src/features/credentials/credentialService.ts`
- **Complexity**: Low
- **Dependencies**: P3-009
- **Description**: Update service for enhanced credential types

---

### Dynamic MCP Server - Core

#### P3-011: Create dynamic server project structure
- **Directory**: `mcp-servers/dynamic-server/`
- **Complexity**: Low
- **Description**: Set up project structure
- **Files**:
  - [ ] server.py
  - [ ] auth.py
  - [ ] token_generator.py
  - [ ] config.py
  - [ ] requirements.txt
  - [ ] Dockerfile
  - [ ] .env.example

---

#### P3-012: Implement FastMCP server base
- **File**: `mcp-servers/dynamic-server/server.py`
- **Complexity**: Medium
- **Dependencies**: P3-011
- **Description**: Basic FastMCP server setup
- **Features**:
  - [ ] FastMCP initialization
  - [ ] SSE transport setup
  - [ ] Startup event handler
  - [ ] Health check endpoint

---

#### P3-013: Implement tool definition fetching
- **File**: `mcp-servers/dynamic-server/server.py`
- **Complexity**: Medium
- **Dependencies**: P3-012, P3-002
- **Description**: Fetch tool definitions from AgentStudio API
- **Features**:
  - [ ] HTTP client to AgentStudio API
  - [ ] Authentication with internal API key
  - [ ] Parse and validate tool definitions
  - [ ] Error handling for API failures

---

#### P3-014: Implement dynamic tool registration
- **File**: `mcp-servers/dynamic-server/server.py`
- **Complexity**: High
- **Dependencies**: P3-013
- **Description**: Dynamically register MCP tools from definitions
- **Features**:
  - [ ] Create tool handler for each definition
  - [ ] Register with FastMCP
  - [ ] Handle parameter types
  - [ ] Support refresh/reload

---

#### P3-015: Implement auth middleware
- **File**: `mcp-servers/dynamic-server/auth.py`
- **Complexity**: Medium
- **Dependencies**: P3-011
- **Description**: Verify requests from AgentStudio
- **Features**:
  - [ ] JWT token verification
  - [ ] Organization ID validation
  - [ ] Rate limiting (optional)

---

#### P3-016: Implement TokenGenerator class
- **File**: `mcp-servers/dynamic-server/token_generator.py`
- **Complexity**: High
- **Dependencies**: P3-011
- **Description**: Generate auth tokens at runtime
- **Methods**:
  - [ ] _static_api_key()
  - [ ] _static_bearer()
  - [ ] _oauth2_client_credentials()
  - [ ] _oauth2_refresh_token()
  - [ ] _jwt_signing()
  - [ ] _session_login()

---

#### P3-017: Implement Redis token caching
- **File**: `mcp-servers/dynamic-server/token_generator.py`
- **Complexity**: Medium
- **Dependencies**: P3-016
- **Description**: Cache generated tokens in Redis
- **Features**:
  - [ ] Redis client setup
  - [ ] Cache with TTL
  - [ ] Auto-refresh before expiry
  - [ ] Handle refresh token rotation

---

#### P3-018: Implement tool execution logic
- **File**: `mcp-servers/dynamic-server/server.py`
- **Complexity**: High
- **Dependencies**: P3-014, P3-016
- **Description**: Execute tool by calling external API
- **Features**:
  - [ ] Build HTTP request from definition
  - [ ] Add auth headers from token generator
  - [ ] Handle GET/POST/PUT/DELETE
  - [ ] Parse and return response
  - [ ] Error handling

---

#### P3-019: Add configuration management
- **File**: `mcp-servers/dynamic-server/config.py`
- **Complexity**: Low
- **Dependencies**: P3-011
- **Description**: Pydantic settings for MCP server
- **Settings**:
  - AGENTSTUDIO_API_URL
  - MCP_SERVER_SECRET
  - MCP_INTERNAL_API_KEY
  - DATABASE_URL (optional)
  - REDIS_URL
  - PORT

---

#### P3-020: Create Dockerfile
- **File**: `mcp-servers/dynamic-server/Dockerfile`
- **Complexity**: Low
- **Dependencies**: P3-011
- **Description**: Docker image for dynamic MCP server
- **Features**:
  - [ ] Python 3.11 base
  - [ ] Install dependencies
  - [ ] Copy source
  - [ ] Expose port 3000
  - [ ] Health check

---

#### P3-021: Create docker-compose for local development
- **File**: `mcp-servers/docker-compose.yml`
- **Complexity**: Low
- **Dependencies**: P3-020
- **Description**: Local development setup
- **Services**:
  - [ ] dynamic-mcp-server
  - [ ] redis
  - [ ] (optional) postgres for testing

---

### Testing

#### P3-022: Unit tests for TokenGenerator
- **File**: `mcp-servers/dynamic-server/tests/test_token_generator.py` (new)
- **Complexity**: Medium
- **Dependencies**: P3-016
- **Description**: Test all token generation methods
- **Tests**:
  - [ ] Static API key
  - [ ] OAuth2 client credentials
  - [ ] OAuth2 refresh token
  - [ ] JWT signing
  - [ ] Token caching
  - [ ] Cache expiry

---

#### P3-023: Unit tests for auth middleware
- **File**: `mcp-servers/dynamic-server/tests/test_auth.py` (new)
- **Complexity**: Low
- **Dependencies**: P3-015
- **Description**: Test JWT verification
- **Tests**:
  - [ ] Valid token
  - [ ] Expired token
  - [ ] Invalid signature
  - [ ] Missing org ID

---

#### P3-024: Integration test for dynamic server
- **File**: `mcp-servers/dynamic-server/tests/test_integration.py` (new)
- **Complexity**: Medium
- **Dependencies**: P3-018
- **Description**: End-to-end test of tool execution
- **Tests**:
  - [ ] Tool discovery
  - [ ] Tool execution with mock API
  - [ ] Auth flow

---

### Deployment

#### P3-025: Azure Container App deployment config
- **File**: `mcp-servers/azure-deploy.yml`
- **Complexity**: Medium
- **Dependencies**: P3-020
- **Description**: Azure deployment configuration
- **Features**:
  - [ ] Container app definition
  - [ ] Custom domain (mcp.agentstudio365.com)
  - [ ] Environment variables
  - [ ] Secrets references
  - [ ] Health check

---

## Task Dependencies Graph

```
Phase 1 (CRITICAL)
P1-001 ─┬─▶ P1-002 ─▶ P1-005
        ├─▶ P1-003
        └─▶ P1-004

Phase 2 (Medium)
P2-001 ─▶ P2-002 ─▶ P2-003
                  ─▶ P2-004 ─▶ P2-005
                            ─▶ P2-006
                            ─▶ P2-007 ─▶ P2-008 ─▶ P2-009
                                              ─▶ P2-010
                                              ─▶ P2-011
                                              ─▶ P2-012

Phase 3 (HIGH)
P3-001 ─▶ P3-002 ─▶ P3-003 ─▶ P3-013
P3-004 ─▶ P3-005 ─▶ P3-006
        ─▶ P3-009 ─▶ P3-010
P3-007 ─▶ P3-008
P3-011 ─▶ P3-012 ─▶ P3-013 ─▶ P3-014 ─▶ P3-018
        ─▶ P3-015 ─▶ P3-023
        ─▶ P3-016 ─▶ P3-017 ─▶ P3-018 ─▶ P3-024
                            ─▶ P3-022
        ─▶ P3-019
        ─▶ P3-020 ─▶ P3-021
                  ─▶ P3-025
```

---

## Sprint Planning Suggestion

### Sprint 1 (Critical Path)
| Task | Description | Points |
|------|-------------|--------|
| P1-001 | Implement _convert_mcp_tool() | 5 |
| P1-002 | Verify LangGraph integration | 3 |
| P1-003 | Add MCP execution logging | 2 |
| P1-004 | Unit tests for tool converter | 3 |
| P1-005 | Integration test | 3 |
| **Total** | | **16** |

### Sprint 2 (Server Registry + Dynamic Server Setup)
| Task | Description | Points |
|------|-------------|--------|
| P2-001 | MCPServer model | 2 |
| P2-002 | MCPServer schemas | 2 |
| P2-003 | Database migration | 2 |
| P2-004 | MCP Servers API | 5 |
| P3-001 | DynamicMCPToolConfig schema | 3 |
| P3-002 | MCP Tools API | 5 |
| P3-011 | Dynamic server structure | 2 |
| **Total** | | **21** |

### Sprint 3 (Dynamic Server Core + Security)
| Task | Description | Points |
|------|-------------|--------|
| P3-004 | CredentialConfig schema | 3 |
| P3-005 | Internal credentials endpoint | 5 |
| P3-012 | FastMCP server base | 3 |
| P3-013 | Tool definition fetching | 5 |
| P3-014 | Dynamic tool registration | 8 |
| P3-015 | Auth middleware | 3 |
| P3-016 | TokenGenerator class | 8 |
| **Total** | | **35** |

### Sprint 4 (UI + Testing + Deployment)
| Task | Description | Points |
|------|-------------|--------|
| P3-007 | Enhanced Tool Modal | 8 |
| P3-009 | Enhanced Credentials Modal | 8 |
| P3-018 | Tool execution logic | 5 |
| P3-020 | Dockerfile | 2 |
| P3-022 | TokenGenerator tests | 3 |
| P3-025 | Azure deployment | 5 |
| **Total** | | **31** |

---

## Quick Reference

### Critical Path (Minimum Viable)
```
P1-001 → P1-002 → DONE (agents can use MCP tools)
```

### Full Feature Path
```
Phase 1 → Phase 3 (skip Phase 2 initially) → Phase 2 (nice to have)
```

### Files to Create (New)
- `backend/app/models/mcp_server.py`
- `backend/app/schemas/mcp_server.py`
- `backend/app/api/v1/mcp_servers.py`
- `backend/app/api/v1/mcp_tools.py`
- `backend/alembic/versions/004_add_mcp_servers.py`
- `backend/alembic/versions/005_enhance_credentials.py`
- `frontend/src/pages/MCPServers.tsx`
- `frontend/src/features/mcp-servers/mcpServerService.ts`
- `frontend/src/components/MCPServers/MCPServerModal.tsx`
- `frontend/src/components/MCPServers/MCPServerCard.tsx`
- `frontend/src/components/Tools/ParametersEditor.tsx`
- `mcp-servers/dynamic-server/*` (entire directory)

### Files to Modify (Existing)
- `backend/app/services/tool_converter.py` - P1-001
- `backend/app/services/langgraph_engine.py` - P1-002
- `backend/app/schemas/tool.py` - P3-001
- `backend/app/schemas/credential.py` - P3-004
- `backend/app/api/v1/credentials.py` - P3-005
- `backend/app/main.py` - P2-005, P3-003
- `frontend/src/App.tsx` - P2-012
- `frontend/src/components/Common/Layout.tsx` - P2-011
- `frontend/src/components/Tools/ToolCreationModal.tsx` - P3-007
- `frontend/src/components/Credentials/CredentialModal.tsx` - P3-009
