# AgentStudio - AI Agent Creation & Management Platform

A React-based platform for creating, managing, and deploying AI agents that connect to existing RAG systems.

## Tech Stack

### Frontend
- **React 18** with TypeScript
- **Vite** for build tooling
- **Ant Design** for UI components
- **ReactFlow** for visual agent builder
- **TailwindCSS** for styling
- **Zustand** for state management
- **TanStack Query** for server state
- **React Hook Form + Zod** for forms & validation

### Backend
- **FastAPI** for REST API
- **LangGraph** for agent orchestration
- **PostgreSQL** for primary database
- **Redis** for caching and sessions
- **SQLAlchemy** for ORM
- **Alembic** for migrations
- **JWT** for authentication

## Project Structure

```
.
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── features/      # Feature modules
│   │   ├── pages/         # Page components
│   │   ├── services/      # API clients
│   │   ├── types/         # TypeScript types
│   │   └── utils/         # Utility functions
│   └── package.json
│
├── backend/               # FastAPI backend
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── core/         # Core configuration
│   │   ├── models/       # Database models
│   │   ├── schemas/      # Pydantic schemas
│   │   └── services/     # Business logic
│   ├── alembic/          # Database migrations
│   └── requirements.txt
│
├── docker-compose.yml    # Docker services
├── PRD.md               # Product Requirements
├── SRS.md               # Software Requirements
└── TASKS.md             # Development tasks
```

## Quick Start

### Using Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd aidemystagent
   ```

2. **Start all services**
   ```bash
   docker-compose up -d
   ```

3. **Access the application**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Manual Setup

#### Backend Setup

1. **Create virtual environment**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start PostgreSQL and Redis**
   ```bash
   # Using Docker
   docker run -d --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:15
   docker run -d --name redis -p 6379:6379 redis:7-alpine
   ```

5. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

6. **Start the server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

#### Frontend Setup

1. **Install dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env if needed
   ```

3. **Start development server**
   ```bash
   npm run dev
   ```

## Development Status

### ✅ Completed

#### Phase 1: Foundation
- ✅ React project with TypeScript and Vite
- ✅ Project structure and folder organization
- ✅ Core dependencies installed and configured
- ✅ ESLint, Prettier, TypeScript configuration
- ✅ Authentication pages (Login, Register, Password Reset)
- ✅ Authentication state management with Zustand
- ✅ Protected route component
- ✅ Main layout with navigation

#### Phase 2: Core Builder
- ✅ Reactflow integration
- ✅ Custom node types (7 types: INPUT, LLM_AGENT, RAG_RETRIEVER, DECISION, TOOL, OUTPUT, SUBGRAPH)
- ✅ Agent builder canvas with drag-and-drop
- ✅ Node library panel
- ✅ Property configuration panel
- ✅ Node connection validation
- ✅ Undo/redo functionality
- ✅ Auto-save structure

#### Phase 3: Backend Integration (In Progress)
- ✅ Python backend project structure
- ✅ FastAPI setup with CORS
- ✅ Database models (User, Organization, Agent, Tool)
- ✅ Pydantic schemas
- ✅ Authentication endpoints (register, login, refresh)
- ✅ Agent CRUD endpoints
- ✅ Tool endpoints (basic)
- ✅ Docker Compose configuration
- 🚧 LangGraph agent engine
- 🚧 Tool execution framework
- 🚧 RAG connector interface
- 🚧 Agent execution API
- 🚧 Frontend-backend integration

### 🔜 Upcoming

#### Phase 4: Testing & Deployment
- Agent templates (5 pre-built)
- Deployment functionality
- Version control
- Analytics dashboard
- Metrics tracking
- User management UI
- Error logging & monitoring

#### Phase 5: Polish & Launch
- Comprehensive error handling
- Loading states & feedback
- Unit & integration tests
- Documentation
- Security audit
- Performance optimization
- Production deployment

## Features

### Implemented

- **User Authentication**: Register, login, password reset
- **Visual Agent Builder**: Drag-and-drop node-based interface
- **7 Node Types**: INPUT, LLM_AGENT, RAG_RETRIEVER, DECISION, TOOL, OUTPUT, SUBGRAPH
- **Property Panel**: Configure node-specific properties
- **Undo/Redo**: History management for canvas changes
- **Responsive Layout**: Sidebar navigation and protected routes
- **API Foundation**: FastAPI with async PostgreSQL and Redis

### Coming Soon

- LangGraph integration for agent execution
- Tool library and management
- RAG system integration
- Real-time agent testing playground
- Analytics and monitoring
- Deployment pipeline

## API Documentation

Once the backend is running, access the interactive API documentation at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Environment Variables

### Backend (.env)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: JWT secret key
- `OPENAI_API_KEY`: OpenAI API key (optional)
- `ANTHROPIC_API_KEY`: Anthropic API key (optional)

### Frontend (.env)
- `VITE_API_BASE_URL`: Backend API URL (default: http://localhost:8000)

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests (when available)
4. Submit a pull request

## License

Proprietary - All rights reserved

## Support

For issues and questions, please create an issue in the repository.
