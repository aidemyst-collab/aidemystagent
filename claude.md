# AgentStudio - Claude Code Context

This document provides comprehensive context for Claude Code and AI assistants working with the AgentStudio codebase.

## Project Overview

**AgentStudio** is an AI Agent Creation & Management Platform that enables users to visually design, build, test, deploy, and manage AI agents with LangGraph orchestration and RAG system integration.

- **Product Name**: AgentStudio
- **Version**: 1.0.0-beta
- **Status**: 90% Complete - Ready for Beta Testing
- **Repository**: aidemystagent

### Core Value Proposition

- Visual drag-and-drop agent builder (ReactFlow-based)
- LangGraph-powered agent orchestration
- RAG system integration via REST/GraphQL
- Multi-environment deployment with versioning
- Real-time testing playground
- Role-based access control
- Production-ready infrastructure

## Technology Stack

### Frontend
- **Framework**: React 18.2 + TypeScript 5.0
- **Build Tool**: Vite 4.4
- **UI Library**: Ant Design 5.0
- **Styling**: TailwindCSS 3.3
- **State Management**: Zustand 4.4 (global), TanStack Query 4.36 (server)
- **Forms**: React Hook Form + Zod validation
- **Routing**: React Router 6.16
- **Flow Builder**: ReactFlow 11.9
- **Dev Server**: http://localhost:5173

### Backend
- **Framework**: FastAPI 0.104
- **Language**: Python 3.11+
- **ORM**: SQLAlchemy 2.0 (async)
- **Database**: PostgreSQL 15+
- **Cache**: Redis 7+
- **Migrations**: Alembic 1.12
- **Agent Engine**: LangGraph 0.2+
- **LLM**: OpenAI, Anthropic
- **HTTP Client**: httpx (async)
- **API Server**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Infrastructure
- **Containers**: Docker + Docker Compose
- **Reverse Proxy**: Nginx
- **Logging**: Python logging with rotation
- **Environment**: .env files

## Architecture

### High-Level Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   React     │─────▶│   FastAPI    │─────▶│ PostgreSQL  │
│  Frontend   │      │   Backend    │      │   Database  │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ├──────▶ Redis (Cache + Sessions)
                            │
                            ├──────▶ LangGraph Engine
                            │
                            └──────▶ External RAG Systems
```

### Key Components

1. **Visual Agent Builder**: ReactFlow canvas with 7 node types
2. **LangGraph Engine**: Orchestrates agent execution with state management
3. **Tool Framework**: Extensible tool system (built-in + custom)
4. **RAG Connectors**: Abstract interface for external RAG systems
5. **Deployment Manager**: Multi-environment deployment with API keys
6. **Version Control**: Git-like versioning for agents
7. **Analytics Dashboard**: Execution metrics and performance tracking

## Directory Structure

```
aidemystagent/
├── frontend/                      # React application
│   ├── src/
│   │   ├── components/
│   │   │   ├── AgentBuilder/     # Visual flow builder (7 nodes)
│   │   │   ├── Common/           # Layout, ProtectedRoute
│   │   │   ├── Credentials/      # Credential management
│   │   │   ├── Deployments/      # Deployment cards/modals
│   │   │   ├── Templates/        # Template gallery
│   │   │   ├── Testing/          # Playgrounds (standard + streaming)
│   │   │   └── Tools/            # Tool library
│   │   ├── features/             # Feature-based modules
│   │   │   ├── agents/           # Agent hooks + service
│   │   │   ├── auth/             # Auth store + hooks + service
│   │   │   ├── credentials/      # Credential service
│   │   │   ├── dashboard/        # Dashboard hooks + service
│   │   │   ├── rag/              # RAG service
│   │   │   ├── tools/            # Tool service
│   │   │   └── workflows/        # Workflow hooks + service
│   │   ├── pages/                # Route pages
│   │   │   ├── AgentBuilder.tsx
│   │   │   ├── Agents.tsx
│   │   │   ├── AgentTest.tsx
│   │   │   ├── Analytics.tsx
│   │   │   ├── Credentials.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Deployments.tsx
│   │   │   ├── Login.tsx
│   │   │   ├── Register.tsx
│   │   │   ├── Templates.tsx
│   │   │   ├── Tools.tsx
│   │   │   ├── Users.tsx
│   │   │   └── WorkflowBuilder.tsx
│   │   ├── services/             # API client
│   │   │   └── api.ts
│   │   └── types/                # TypeScript definitions
│   │       ├── agent.ts
│   │       ├── auth.ts
│   │       ├── nodeSchemas.ts
│   │       └── workflow.ts
│   └── package.json
│
├── backend/                       # FastAPI application
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py           # Dependency injection
│   │   │   └── v1/               # API v1 endpoints
│   │   │       ├── agents.py
│   │   │       ├── analytics.py
│   │   │       ├── auth.py
│   │   │       ├── credentials.py
│   │   │       ├── dashboard.py
│   │   │       ├── deployments.py
│   │   │       ├── execute.py
│   │   │       ├── organizations.py
│   │   │       ├── rag.py
│   │   │       ├── templates.py
│   │   │       ├── tools.py
│   │   │       ├── users.py
│   │   │       ├── versions.py
│   │   │       └── workflows.py
│   │   ├── core/                 # Core configuration
│   │   │   ├── config.py         # Settings (Pydantic)
│   │   │   ├── database.py       # PostgreSQL setup
│   │   │   ├── logging_config.py
│   │   │   ├── redis_client.py
│   │   │   └── security.py       # JWT + password hashing
│   │   ├── middleware/
│   │   │   ├── error_handler.py
│   │   │   └── request_logger.py
│   │   ├── models/               # SQLAlchemy ORM models
│   │   │   ├── agent.py
│   │   │   ├── credential.py
│   │   │   ├── deployment.py
│   │   │   ├── tool.py
│   │   │   ├── user.py
│   │   │   ├── vector_store.py
│   │   │   └── version.py
│   │   ├── schemas/              # Pydantic schemas (request/response)
│   │   │   ├── agent.py
│   │   │   ├── credential.py
│   │   │   ├── deployment.py
│   │   │   ├── tool.py
│   │   │   ├── user.py
│   │   │   ├── version.py
│   │   │   └── workflow.py
│   │   ├── services/             # Business logic
│   │   │   ├── file_reader.py
│   │   │   ├── langgraph_engine.py   # CRITICAL: Agent orchestration
│   │   │   ├── llm_client.py
│   │   │   ├── memory_manager.py
│   │   │   ├── rag_connector.py      # RAG system integration
│   │   │   ├── rag_service.py
│   │   │   ├── template_engine.py
│   │   │   ├── templates.py          # Agent templates
│   │   │   ├── tool_converter.py
│   │   │   └── tools/                # Tool implementations
│   │   │       ├── base.py           # BaseTool abstract class
│   │   │       ├── calculator.py
│   │   │       ├── datetime_tool.py
│   │   │       ├── json_parser.py
│   │   │       ├── web_search.py
│   │   │       └── api_integration.py
│   │   └── main.py               # FastAPI app entry point
│   ├── alembic/                  # Database migrations
│   │   ├── versions/
│   │   │   ├── 001_initial.py
│   │   │   ├── 002_add_credentials_table.py
│   │   │   └── 003_add_mcp_tool_type.py
│   │   └── env.py
│   └── requirements.txt
│
├── docs/                          # Documentation
│   ├── API_DOCUMENTATION.md      # Complete API reference
│   ├── DEPLOYMENT.md             # Production deployment guide
│   ├── PRD.md                    # Product requirements
│   ├── SRS.md                    # Software requirements
│   ├── USER_GUIDE.md             # End-user documentation
│   ├── PROJECT_STATUS.md         # Project status report
│   └── DEVELOPMENT_STATUS.md
│
├── docker-compose.yml            # Development setup
├── README.md                     # Quick start guide
└── .env.example                  # Environment template
```

## Node Types (Agent Builder)

The visual agent builder supports 7 node types:

1. **INPUT**: Entry point, initializes agent state with user query
2. **LLM_AGENT**: Core LLM agent with tool binding capabilities
3. **RAG_RETRIEVER**: Retrieval-augmented generation for knowledge access
4. **DECISION**: Conditional routing based on state/conditions
5. **TOOL**: Executes specific tools (Calculator, DateTime, JSONParser, WebSearch, etc.)
6. **OUTPUT**: Final response formatting and delivery
7. **SUBGRAPH**: Nested agent workflows for complex operations

### Additional Node Types (UI)
- **AUXILIARY**: Helper nodes for specific tasks
- **FILE_READER**: File reading and processing
- **MEMORY**: State persistence and retrieval

## Database Schema

### Core Tables

```
users
├── id (UUID, PK)
├── email (unique)
├── hashed_password
├── full_name
├── role (admin, creator, viewer)
├── organization_id (FK)
└── is_active

organizations
├── id (UUID, PK)
├── name
└── created_at

agents
├── id (UUID, PK)
├── name
├── description
├── creator_id (FK → users)
├── organization_id (FK → organizations)
├── configuration (JSONB)  # Node/edge data
├── status (draft, deployed, archived)
├── version
└── created_at, updated_at

tools
├── id (UUID, PK)
├── name
├── type (built-in, custom, api, mcp)
├── configuration (JSONB)
├── creator_id (FK)
├── organization_id (FK)
└── created_at

deployments
├── id (UUID, PK)
├── agent_id (FK → agents)
├── environment (dev, staging, production)
├── status (active, inactive, failed)
├── api_key
├── endpoint_url
└── deployed_at

versions
├── id (UUID, PK)
├── agent_id (FK → agents)
├── version_number
├── configuration (JSONB)
├── changelog
└── created_at

credentials
├── id (UUID, PK)
├── name
├── type (api_key, oauth2, basic)
├── encrypted_value
├── organization_id (FK)
└── created_at

executions (tracking)
├── id (UUID, PK)
├── agent_id (FK)
├── user_id (FK)
├── input (JSONB)
├── output (JSONB)
├── execution_time_ms
├── token_usage
└── executed_at
```

## API Endpoints

Base URL: `http://localhost:8000/api/v1`

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - Login (returns access + refresh tokens)
- `POST /auth/refresh` - Refresh access token

### Users
- `GET /users` - List users (admin only)
- `POST /users` - Create user (admin only)
- `PATCH /users/{id}` - Update user
- `DELETE /users/{id}` - Delete user (admin only)

### Organizations
- `GET /organizations` - List organizations
- `POST /organizations` - Create organization
- `GET /organizations/{id}` - Get organization details

### Agents
- `GET /agents` - List agents (filtered by user/org)
- `POST /agents` - Create agent
- `GET /agents/{id}` - Get agent details
- `PATCH /agents/{id}` - Update agent
- `DELETE /agents/{id}` - Delete agent

### Workflows (similar to agents)
- `GET /workflows` - List workflows
- `POST /workflows` - Create workflow
- `GET /workflows/{id}` - Get workflow
- `PATCH /workflows/{id}` - Update workflow
- `DELETE /workflows/{id}` - Delete workflow

### Tools
- `GET /tools/built-in` - List built-in tools
- `GET /tools/built-in/{name}` - Get tool details
- `POST /tools/built-in/{name}/execute` - Execute tool
- `GET /tools/custom` - List custom tools
- `POST /tools/custom` - Create custom tool

### Credentials
- `GET /credentials` - List credentials
- `POST /credentials` - Create credential
- `GET /credentials/{id}` - Get credential (masked)
- `DELETE /credentials/{id}` - Delete credential

### RAG
- `POST /rag/test` - Test RAG connection
- `POST /rag/query` - Query RAG system

### Execution
- `POST /execute/{agent_id}` - Execute agent (standard)
- `POST /execute/{agent_id}/stream` - Execute with SSE streaming

### Templates
- `GET /templates` - List agent templates
- `GET /templates/{id}` - Get template details
- `POST /templates/{id}/clone` - Clone template to new agent

### Deployments
- `GET /deployments` - List deployments
- `POST /deployments` - Create deployment
- `GET /deployments/{id}` - Get deployment
- `PATCH /deployments/{id}` - Update deployment
- `DELETE /deployments/{id}` - Delete deployment
- `POST /deployments/{id}/stop` - Stop deployment
- `POST /deployments/{id}/restart` - Restart deployment

### Versions
- `GET /agents/{id}/versions` - List agent versions
- `POST /agents/{id}/versions` - Create version snapshot
- `GET /agents/{id}/versions/{version}` - Get specific version
- `POST /agents/{id}/versions/{version}/restore` - Restore version
- `GET /agents/{id}/versions/compare/{v1}/{v2}` - Compare versions

### Analytics
- `GET /analytics` - Get system analytics
- `GET /analytics/agents/{id}` - Get agent-specific analytics

### Dashboard
- `GET /dashboard/stats` - Get dashboard statistics
- `GET /dashboard/recent` - Get recent activity

## LangGraph Engine

### Key File
`backend/app/services/langgraph_engine.py`

### Workflow Pattern

1. **State Schema**: Defines agent state structure
2. **Node Functions**: Handlers for each node type
3. **StateGraph**: Builds execution graph
4. **Edges**: Connects nodes (normal + conditional)
5. **Checkpointing**: Redis-based state persistence
6. **Tool Binding**: Automatic tool routing

### Execution Flow

```
INPUT → LLM_AGENT (with tools) → TOOL → LLM_AGENT (results) → OUTPUT
          ↓
    RAG_RETRIEVER (if needed)
          ↓
       DECISION (conditional routing)
```

## Tool System

### Base Tool Class
`backend/app/services/tools/base.py`

All tools inherit from `BaseTool` with:
- `name: str`
- `description: str`
- `input_schema: dict`
- `execute(params: dict) -> dict`

### Built-in Tools

1. **Calculator** (`calculator.py`): Math operations
2. **DateTime** (`datetime_tool.py`): Date/time utilities
3. **JSONParser** (`json_parser.py`): JSON parsing/extraction
4. **WebSearch** (`web_search.py`): Web search (mock)
5. **APIIntegration** (`api_integration.py`): REST API calls

### Tool Registration

Tools are registered in `tools/__init__.py` and exposed via:
- `GET /tools/built-in` - Lists available tools
- `POST /tools/built-in/{name}/execute` - Executes a specific tool

## RAG Integration

### Key File
`backend/app/services/rag_connector.py`

### Connector Types

1. **RESTRAGConnector**: REST API connections
2. **GraphQLRAGConnector**: GraphQL endpoints

### Configuration

```python
{
  "type": "rest",  # or "graphql"
  "endpoint": "https://rag.example.com/search",
  "auth": {
    "type": "api_key",  # or "basic", "oauth2"
    "key": "...",
    "header": "Authorization"
  },
  "search_params": {
    "top_k": 5,
    "threshold": 0.7
  }
}
```

## Authentication & Authorization

### JWT Token Flow

1. User logs in: `POST /auth/login`
2. Receives: `{ access_token, refresh_token }`
3. Includes in requests: `Authorization: Bearer {access_token}`
4. Refresh when expired: `POST /auth/refresh`

### Roles

- **Admin**: Full system access, user management
- **Creator**: Create/edit/delete own agents, deploy
- **Viewer**: Read-only access, test agents

### Implementation

- Passwords: Bcrypt hashing
- Tokens: JWT with HS256
- Access Token: 15 minutes expiry
- Refresh Token: 7 days expiry

## Frontend State Management

### Zustand Stores

**Auth Store** (`features/auth/authStore.ts`):
```typescript
{
  user: User | null,
  token: string | null,
  login: (email, password) => Promise<void>,
  logout: () => void,
  register: (data) => Promise<void>
}
```

### TanStack Query

Used for server state (agents, tools, deployments, etc.):
- Automatic caching
- Background refetching
- Optimistic updates
- Error handling

Example:
```typescript
const { data, isLoading } = useQuery({
  queryKey: ['agents'],
  queryFn: agentService.getAgents
});
```

## Development Workflow

### Starting the Application

```bash
# Using Docker (recommended)
docker-compose up -d

# Manual - Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Manual - Frontend
cd frontend
npm install
npm run dev
```

### Environment Variables

**Backend** (`.env`):
```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/agentstudio
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

**Frontend** (`.env`):
```
VITE_API_BASE_URL=http://localhost:8000
```

### Database Migrations

```bash
cd backend

# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Common Development Tasks

#### Add a New API Endpoint

1. Create schema in `backend/app/schemas/`
2. Add route in `backend/app/api/v1/{module}.py`
3. Update router inclusion in `backend/app/main.py`
4. Create service in `frontend/src/features/{module}/`
5. Add to API client in `frontend/src/services/api.ts`

#### Add a New Node Type

1. Create node component in `frontend/src/components/AgentBuilder/nodes/`
2. Export from `frontend/src/components/AgentBuilder/nodes/index.ts`
3. Add to node types in `frontend/src/types/nodeSchemas.ts`
4. Update LangGraph engine handler in `backend/app/services/langgraph_engine.py`

#### Add a New Tool

1. Create tool class in `backend/app/services/tools/{name}.py`
2. Inherit from `BaseTool`
3. Implement `execute()` method
4. Register in `backend/app/services/tools/__init__.py`
5. Update tool service in `frontend/src/features/tools/toolService.ts`

## Testing

### Current Status
⚠️ **Testing is incomplete** - Unit and integration tests are pending

### Testing Strategy (Planned)

**Backend**:
- Unit tests: pytest
- Integration tests: pytest + TestClient
- Coverage target: 80%+

**Frontend**:
- Unit tests: Vitest + React Testing Library
- E2E tests: Playwright or Cypress
- Coverage target: 70%+

### Test Commands (When Implemented)

```bash
# Backend
cd backend
pytest
pytest --cov=app tests/

# Frontend
cd frontend
npm test
npm run test:coverage
```

## Deployment

### Production Checklist

1. ✅ Environment variables configured
2. ✅ Database migrations applied
3. ✅ SSL/TLS certificates installed
4. ✅ CORS origins restricted
5. ⏳ Security audit completed
6. ⏳ Load testing performed
7. ✅ Monitoring configured
8. ✅ Backup strategy implemented
9. ⏳ Rate limiting enabled
10. ✅ Error logging active

### Docker Deployment

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Configuration

See `DEPLOYMENT.md` for detailed production setup including:
- Nginx reverse proxy
- SSL/TLS setup
- Database optimization
- Redis configuration
- Monitoring and logging
- Scaling strategies

## Known Issues & Limitations

1. **Testing**: No unit/integration tests implemented yet
2. **RAG Connectors**: Only REST/GraphQL (no native vector DB)
3. **Tool Library**: Limited to 4 built-in tools
4. **Scalability**: Single-node deployment (horizontal scaling documented)
5. **LLM Support**: OpenAI and Anthropic only
6. **Rate Limiting**: Configured but not enforced
7. **Metrics**: Basic analytics (no APM integration)

## Important Context for AI Assistants

### When Working on Agent Builder
- ReactFlow is the foundation - avoid breaking node/edge structure
- All node types must have corresponding LangGraph handlers
- Property panel validation uses Zod schemas
- Auto-save triggers on every change (debounced)

### When Working on LangGraph Engine
- State schema must match node configurations
- Checkpointing uses Redis for persistence
- Tool binding happens automatically via LangGraph
- Error handling must preserve execution state

### When Working on API Endpoints
- All routes use async/await pattern
- JWT dependency injection via `get_current_user`
- Pydantic schemas for validation
- Return proper HTTP status codes

### When Working on Frontend Components
- Use Ant Design components consistently
- TanStack Query for all server state
- React Hook Form + Zod for forms
- TailwindCSS for custom styling

### Code Style
- **Backend**: PEP 8, type hints, async/await
- **Frontend**: ESLint + Prettier, functional components, TypeScript strict mode

## Useful Commands

```bash
# Backend
cd backend
alembic upgrade head              # Apply migrations
alembic revision --autogenerate   # Create migration
uvicorn app.main:app --reload     # Start dev server
python -m pytest                  # Run tests (when available)

# Frontend
cd frontend
npm run dev                       # Start dev server
npm run build                     # Build for production
npm run preview                   # Preview production build
npm run lint                      # Run linter

# Docker
docker-compose up -d              # Start all services
docker-compose logs -f backend    # View backend logs
docker-compose logs -f frontend   # View frontend logs
docker-compose down               # Stop all services
docker-compose restart backend    # Restart backend only

# Database
docker exec -it postgres_container psql -U postgres -d agentstudio
```

## Documentation Files

- **README.md**: Quick start and overview
- **PRD.md**: Product requirements (comprehensive)
- **SRS.md**: Software requirements specification
- **API_DOCUMENTATION.md**: Complete API reference with examples
- **USER_GUIDE.md**: End-user documentation
- **DEPLOYMENT.md**: Production deployment guide
- **PROJECT_STATUS.md**: Current project status (90% complete)

## Contact & Support

For issues, questions, or contributions:
1. Check existing documentation
2. Review API docs at http://localhost:8000/docs
3. Examine relevant code files
4. Create detailed issue reports with context

---

**Last Updated**: 2025-12-06
**Project Status**: 90% Complete - Ready for Beta Testing
**Next Phase**: Testing, Security Audit, Performance Optimization
