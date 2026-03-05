from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings
from app.core.logging_config import logger
from app.api.v1 import auth, agents, tools, execute, templates, deployments, versions, analytics, dashboard, workflows, credentials, organizations, users, rag, admin, invitations, audit, twilio, voice, whatsapp, public_invoke, mcp_servers, mcp_tools
from app.middleware.error_handler import (
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler,
)
from app.middleware.request_logger import log_requests

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    description="AI Agent Creation & Management Platform API",
    docs_url="/docs",
    redoc_url="/redoc",
    redirect_slashes=False,
)

# Exception handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Request logging middleware
app.middleware("http")(log_requests)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_PREFIX}/users", tags=["users"])
app.include_router(organizations.router, prefix=f"{settings.API_V1_PREFIX}/organizations", tags=["organizations"])
app.include_router(agents.router, prefix=f"{settings.API_V1_PREFIX}/agents", tags=["agents"])
app.include_router(workflows.router, prefix=f"{settings.API_V1_PREFIX}/workflows", tags=["workflows"])
app.include_router(tools.router, prefix=f"{settings.API_V1_PREFIX}/tools", tags=["tools"])
app.include_router(credentials.router, prefix=f"{settings.API_V1_PREFIX}/credentials", tags=["credentials"])
app.include_router(rag.router, prefix=f"{settings.API_V1_PREFIX}/rag", tags=["rag"])
app.include_router(execute.router, prefix=f"{settings.API_V1_PREFIX}/execute", tags=["execute"])
app.include_router(templates.router, prefix=f"{settings.API_V1_PREFIX}/templates", tags=["templates"])
app.include_router(deployments.router, prefix=f"{settings.API_V1_PREFIX}/deployments", tags=["deployments"])
app.include_router(versions.router, prefix=f"{settings.API_V1_PREFIX}", tags=["versions"])
app.include_router(analytics.router, prefix=f"{settings.API_V1_PREFIX}", tags=["analytics"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_PREFIX}", tags=["dashboard"])
app.include_router(admin.router, prefix=f"{settings.API_V1_PREFIX}/admin", tags=["admin"])
app.include_router(invitations.router, prefix=f"{settings.API_V1_PREFIX}/invitations", tags=["invitations"])
app.include_router(audit.router, prefix=f"{settings.API_V1_PREFIX}/audit", tags=["audit"])
app.include_router(twilio.router, prefix=f"{settings.API_V1_PREFIX}/twilio", tags=["twilio"])
app.include_router(voice.router, prefix=f"{settings.API_V1_PREFIX}/voice", tags=["voice"])
app.include_router(whatsapp.router, prefix=f"{settings.API_V1_PREFIX}", tags=["whatsapp"])
app.include_router(mcp_servers.router, prefix=f"{settings.API_V1_PREFIX}/mcp-servers", tags=["mcp-servers"])
app.include_router(mcp_tools.router, prefix=f"{settings.API_V1_PREFIX}/mcp-tools", tags=["mcp-tools"])

# Public API routes (organization-scoped, API key auth)
app.include_router(public_invoke.router, prefix=f"{settings.API_V1_PREFIX}", tags=["public"])


@app.get("/")
async def root():
    return {"message": "AgentStudio API", "version": settings.APP_VERSION}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
