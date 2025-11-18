from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import auth, agents, tools, execute, templates, deployments, versions, analytics

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
)

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
app.include_router(agents.router, prefix=f"{settings.API_V1_PREFIX}/agents", tags=["agents"])
app.include_router(tools.router, prefix=f"{settings.API_V1_PREFIX}/tools", tags=["tools"])
app.include_router(execute.router, prefix=f"{settings.API_V1_PREFIX}/execute", tags=["execute"])
app.include_router(templates.router, prefix=f"{settings.API_V1_PREFIX}/templates", tags=["templates"])
app.include_router(deployments.router, prefix=f"{settings.API_V1_PREFIX}/deployments", tags=["deployments"])
app.include_router(versions.router, prefix=f"{settings.API_V1_PREFIX}", tags=["versions"])
app.include_router(analytics.router, prefix=f"{settings.API_V1_PREFIX}", tags=["analytics"])


@app.get("/")
async def root():
    return {"message": "AgentStudio API", "version": settings.APP_VERSION}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
