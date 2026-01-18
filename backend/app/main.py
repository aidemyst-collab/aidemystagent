from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings
from app.core.logging_config import logger
from app.api.v1 import auth, agents, tools, execute, templates, deployments, versions, analytics, dashboard, workflows, credentials, organizations, users, rag, admin, invitations, audit, twilio, voice, whatsapp
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


@app.get("/")
async def root():
    return {"message": "AgentStudio API", "version": settings.APP_VERSION}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/setup/seed-admin")
async def seed_admin_user(secret: str):
    """
    One-time endpoint to seed the platform admin user.
    Protected by secret key. Remove after use.
    """
    import os
    from sqlalchemy import text
    from passlib.context import CryptContext
    from app.core.database import async_engine

    # Verify secret (use environment variable or hardcoded for initial setup)
    expected_secret = os.getenv("SETUP_SECRET", "agentstudio-setup-2026")
    if secret != expected_secret:
        return {"error": "Invalid secret"}

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    ADMIN_EMAIL = "admin@agentstudio.io"
    ADMIN_PASSWORD = "AgentStudio@2026!"
    ADMIN_FULL_NAME = "Platform Administrator"
    ORG_NAME = "AgentStudio"

    password_hash = pwd_context.hash(ADMIN_PASSWORD)

    async with async_engine.begin() as conn:
        # Check if admin exists
        result = await conn.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": ADMIN_EMAIL}
        )
        existing = result.fetchone()

        if existing:
            return {"message": "Admin user already exists", "email": ADMIN_EMAIL}

        # Check/create organization
        result = await conn.execute(
            text("SELECT id FROM organizations WHERE name = :name"),
            {"name": ORG_NAME}
        )
        org = result.fetchone()

        if not org:
            # Get starter plan
            result = await conn.execute(
                text("SELECT id FROM subscription_plans WHERE name = 'starter' LIMIT 1")
            )
            plan = result.fetchone()
            plan_id = plan[0] if plan else None

            await conn.execute(
                text("""
                    INSERT INTO organizations (id, name, slug, subscription_plan_id, subscription_status, is_active, created_at, updated_at)
                    VALUES (gen_random_uuid(), :name, :slug, :plan_id, 'active', true, NOW(), NOW())
                """),
                {"name": ORG_NAME, "slug": "agentstudio", "plan_id": plan_id}
            )

        # Get org id
        result = await conn.execute(
            text("SELECT id FROM organizations WHERE name = :name"),
            {"name": ORG_NAME}
        )
        org = result.fetchone()
        org_id = org[0]

        # Create admin user
        await conn.execute(
            text("""
                INSERT INTO users (
                    id, organization_id, email, hashed_password, role,
                    full_name, is_platform_admin, is_active, email_verified,
                    created_at, updated_at
                )
                VALUES (
                    gen_random_uuid(), :org_id, :email, :password_hash, 'ADMIN',
                    :full_name, true, true, true,
                    NOW(), NOW()
                )
            """),
            {
                "org_id": org_id,
                "email": ADMIN_EMAIL,
                "password_hash": password_hash,
                "full_name": ADMIN_FULL_NAME
            }
        )

        # Get user id and assign org_owner role
        result = await conn.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": ADMIN_EMAIL}
        )
        user = result.fetchone()
        user_id = user[0]

        result = await conn.execute(
            text("SELECT id FROM roles WHERE name = 'org_owner' AND is_system_role = true LIMIT 1")
        )
        role = result.fetchone()

        if role:
            role_id = role[0]
            await conn.execute(
                text("""
                    INSERT INTO user_roles (id, user_id, role_id, organization_id, assigned_at)
                    VALUES (gen_random_uuid(), :user_id, :role_id, :org_id, NOW())
                    ON CONFLICT DO NOTHING
                """),
                {"user_id": user_id, "role_id": role_id, "org_id": org_id}
            )

    return {
        "message": "Admin user created successfully",
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
        "note": "Please change password after first login and remove this endpoint"
    }
