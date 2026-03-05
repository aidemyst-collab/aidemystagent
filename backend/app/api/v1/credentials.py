"""
API endpoints for credential management
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID
import httpx
import json

from app.core.database import get_db
from app.models.credential import Credential, CredentialProvider
from app.models.user import User
from app.schemas.credential import (
    CredentialCreate,
    CredentialUpdate,
    CredentialResponse,
    CredentialListResponse,
    CredentialTestRequest,
    CredentialTestResponse,
)
from app.api.deps import get_current_active_user, require_permission, get_effective_organization_id


router = APIRouter()


@router.get("", response_model=CredentialListResponse)
async def list_credentials(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("credentials:read")),
    skip: int = 0,
    limit: int = 100,
    provider: Optional[CredentialProvider] = None,
):
    """
    List all credentials for the effective organization (supports admin org switching)
    """
    # Build query (using effective org for platform admin switching)
    query = select(Credential).where(
        Credential.organization_id == effective_org_id
    )

    if provider:
        query = query.where(Credential.provider == provider)

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    credentials = result.scalars().all()

    # Get total count
    count_query = select(func.count(Credential.id)).where(
        Credential.organization_id == effective_org_id
    )
    if provider:
        count_query = count_query.where(Credential.provider == provider)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Convert to response with masked API keys
    credential_responses = [
        CredentialResponse.from_orm_with_preview(cred) for cred in credentials
    ]

    return CredentialListResponse(credentials=credential_responses, total=total)


@router.get("/{credential_id}", response_model=CredentialResponse)
async def get_credential(
    credential_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("credentials:read")),
):
    """
    Get a specific credential by ID
    """
    result = await db.execute(
        select(Credential).where(Credential.id == credential_id)
    )
    credential = result.scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    # Check access permissions (using effective org for platform admin switching)
    if credential.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this credential",
        )

    return CredentialResponse.from_orm_with_preview(credential)


@router.post("", response_model=CredentialResponse, status_code=status.HTTP_201_CREATED)
async def create_credential(
    credential_data: CredentialCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("credentials:create")),
):
    """
    Create a new credential
    """
    # Check if credential with same name already exists for this organization (using effective org)
    existing = await db.execute(
        select(Credential).where(
            Credential.organization_id == effective_org_id,
            Credential.name == credential_data.name,
        )
    )

    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A credential with this name already exists",
        )

    # Determine credential value based on provider type
    # For database/voice/messaging providers, serialize connection_config to JSON
    # For LLM providers, use the api_key directly
    config_providers = [
        CredentialProvider.REDIS, CredentialProvider.POSTGRESQL, CredentialProvider.MONGODB,
        CredentialProvider.TWILIO, CredentialProvider.ETISALAT, CredentialProvider.WHATSAPP_META
    ]
    if credential_data.provider in config_providers:
        # Database/voice/messaging credential - serialize connection config to JSON
        credential_value = json.dumps(credential_data.connection_config)
    else:
        # LLM credential - use api_key
        credential_value = credential_data.api_key

    # Create new credential (using effective org for platform admin switching)
    # TODO: Encrypt credential value before storing
    new_credential = Credential(
        user_id=current_user.id,
        organization_id=effective_org_id,
        name=credential_data.name,
        provider=credential_data.provider,
        api_key=credential_value,  # In production, encrypt this
        api_base=credential_data.api_base,
        api_version=credential_data.api_version,
        organization_key=credential_data.organization_key,
        is_active="active",
    )

    db.add(new_credential)
    await db.commit()
    await db.refresh(new_credential)

    return CredentialResponse.from_orm_with_preview(new_credential)


@router.put("/{credential_id}", response_model=CredentialResponse)
async def update_credential(
    credential_id: str,
    credential_data: CredentialUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("credentials:update")),
):
    """
    Update a credential
    """
    result = await db.execute(
        select(Credential).where(Credential.id == credential_id)
    )
    credential = result.scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    # Check access permissions (using effective org for platform admin switching)
    if credential.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this credential",
        )

    # Update fields
    update_data = credential_data.model_dump(exclude_unset=True)

    # Handle connection_config for database credentials
    if 'connection_config' in update_data and update_data['connection_config'] is not None:
        # Serialize connection_config to JSON and store in api_key field
        update_data['api_key'] = json.dumps(update_data['connection_config'])
        del update_data['connection_config']

    for field, value in update_data.items():
        setattr(credential, field, value)

    await db.commit()
    await db.refresh(credential)

    return CredentialResponse.from_orm_with_preview(credential)


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(
    credential_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("credentials:delete")),
):
    """
    Delete a credential
    """
    result = await db.execute(
        select(Credential).where(Credential.id == credential_id)
    )
    credential = result.scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    # Check access permissions (using effective org for platform admin switching)
    if credential.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this credential",
        )

    await db.delete(credential)
    await db.commit()

    return None


@router.post("/test", response_model=CredentialTestResponse)
async def test_credential(
    test_request: CredentialTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("credentials:read")),
):
    """
    Test a credential by making a simple API call to the provider
    Can test with provided credentials OR use stored credential by ID
    """
    try:
        # If credential_id is provided, fetch the stored credential
        if test_request.credential_id:
            result = await db.execute(
                select(Credential).where(Credential.id == test_request.credential_id)
            )
            credential = result.scalar_one_or_none()

            if not credential:
                return CredentialTestResponse(
                    success=False,
                    message="Credential not found",
                )

            # Check access permissions (using effective org for platform admin switching)
            if credential.organization_id != effective_org_id:
                return CredentialTestResponse(
                    success=False,
                    message="You don't have access to this credential",
                )

            # Use stored credential values
            test_request.provider = credential.provider
            test_request.api_base = credential.api_base
            test_request.api_version = credential.api_version

            # Determine if it's a config-based credential (database/voice/messaging)
            config_providers = [
                CredentialProvider.REDIS, CredentialProvider.POSTGRESQL, CredentialProvider.MONGODB,
                CredentialProvider.TWILIO, CredentialProvider.ETISALAT, CredentialProvider.WHATSAPP_META
            ]
            is_config_based = credential.provider in config_providers

            if is_config_based:
                # Deserialize connection config from JSON
                import json
                test_request.connection_config = json.loads(credential.api_key)
            else:
                # Use the stored API key
                test_request.api_key = credential.api_key

        # Check if we have the necessary credentials based on provider type
        config_providers = [
            CredentialProvider.REDIS, CredentialProvider.POSTGRESQL, CredentialProvider.MONGODB,
            CredentialProvider.TWILIO, CredentialProvider.ETISALAT, CredentialProvider.WHATSAPP_META
        ]
        is_config_based = test_request.provider in config_providers

        if not is_config_based and not test_request.api_key:
            return CredentialTestResponse(
                success=False,
                message="API key is required to test LLM credentials",
            )

        if is_config_based and not test_request.connection_config:
            return CredentialTestResponse(
                success=False,
                message="Connection configuration is required to test this credential type",
            )

        if test_request.provider == CredentialProvider.OPENAI:
            # Test OpenAI credential
            api_base = test_request.api_base or "https://api.openai.com/v1"
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{api_base}/models",
                    headers={"Authorization": f"Bearer {test_request.api_key}"},
                    timeout=10.0,
                )
                if response.status_code == 200:
                    return CredentialTestResponse(
                        success=True,
                        message="OpenAI credential is valid",
                        details={"models_count": len(response.json().get("data", []))},
                    )
                else:
                    return CredentialTestResponse(
                        success=False,
                        message=f"Failed to authenticate: {response.text}",
                    )

        elif test_request.provider == CredentialProvider.ANTHROPIC:
            # Test Anthropic credential
            api_base = test_request.api_base or "https://api.anthropic.com/v1"
            async with httpx.AsyncClient() as client:
                # Anthropic doesn't have a models endpoint, so we'll make a minimal completion request
                response = await client.post(
                    f"{api_base}/messages",
                    headers={
                        "x-api-key": test_request.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-3-haiku-20240307",
                        "max_tokens": 10,
                        "messages": [{"role": "user", "content": "Hi"}],
                    },
                    timeout=10.0,
                )
                if response.status_code == 200:
                    return CredentialTestResponse(
                        success=True,
                        message="Anthropic credential is valid",
                    )
                else:
                    return CredentialTestResponse(
                        success=False,
                        message=f"Failed to authenticate: {response.text}",
                    )

        elif test_request.provider == CredentialProvider.REDIS:
            # Test Redis connection
            try:
                import redis.asyncio as aioredis
                config = test_request.connection_config or {}
                host = config.get('host', 'localhost')
                port = int(config.get('port', 6379))
                password = config.get('password')
                db = int(config.get('database', 0))

                redis_client = aioredis.Redis(
                    host=host,
                    port=port,
                    password=password,
                    db=db,
                    decode_responses=True,
                )
                await redis_client.ping()
                await redis_client.close()

                return CredentialTestResponse(
                    success=True,
                    message="Redis connection successful",
                    details={"host": host, "port": port, "database": db},
                )
            except ImportError:
                return CredentialTestResponse(
                    success=False,
                    message="Redis library not installed. Install with: pip install redis",
                )
            except Exception as e:
                return CredentialTestResponse(
                    success=False,
                    message=f"Redis connection failed: {str(e)}",
                )

        elif test_request.provider == CredentialProvider.POSTGRESQL:
            # Test PostgreSQL connection
            try:
                import asyncpg
                config = test_request.connection_config or {}

                # Try connection string first, then individual fields
                if 'connection_string' in config and config['connection_string']:
                    dsn = config['connection_string']
                else:
                    host = config.get('host', 'localhost')
                    port = int(config.get('port', 5432))
                    database = config.get('database', 'postgres')
                    user = config.get('username', 'postgres')
                    password = config.get('password', '')
                    dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}"

                conn = await asyncpg.connect(dsn, timeout=10.0)
                version = await conn.fetchval('SELECT version()')
                await conn.close()

                return CredentialTestResponse(
                    success=True,
                    message="PostgreSQL connection successful",
                    details={"version": version[:50]},
                )
            except ImportError:
                return CredentialTestResponse(
                    success=False,
                    message="PostgreSQL library not installed. Install with: pip install asyncpg",
                )
            except Exception as e:
                return CredentialTestResponse(
                    success=False,
                    message=f"PostgreSQL connection failed: {str(e)}",
                )

        elif test_request.provider == CredentialProvider.MONGODB:
            # Test MongoDB connection
            try:
                from motor.motor_asyncio import AsyncIOMotorClient
                config = test_request.connection_config or {}
                uri = config.get('connection_uri', 'mongodb://localhost:27017')
                database = config.get('database', 'test')

                client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=10000)
                # Test connection by getting server info
                await client.admin.command('ping')
                db_names = await client.list_database_names()
                client.close()

                return CredentialTestResponse(
                    success=True,
                    message="MongoDB connection successful",
                    details={"database": database, "databases_count": len(db_names)},
                )
            except ImportError:
                return CredentialTestResponse(
                    success=False,
                    message="MongoDB library not installed. Install with: pip install motor",
                )
            except Exception as e:
                return CredentialTestResponse(
                    success=False,
                    message=f"MongoDB connection failed: {str(e)}",
                )

        else:
            return CredentialTestResponse(
                success=False,
                message=f"Testing not yet implemented for provider: {test_request.provider}",
            )

    except httpx.TimeoutException:
        return CredentialTestResponse(
            success=False,
            message="Request timed out",
        )
    except Exception as e:
        return CredentialTestResponse(
            success=False,
            message=f"Error testing credential: {str(e)}",
        )


# ============================================================================
# Internal API for Dynamic MCP Server
# ============================================================================

@router.get("/internal/{credential_id}")
async def get_credential_internal(
    credential_id: str,
    x_internal_key: str = None,
    x_organization_id: str = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Internal endpoint for Dynamic MCP Server to fetch decrypted credentials.

    This endpoint is used by the Dynamic MCP Server to get the actual credential
    values at runtime. The LLM never sees these values - only tool names.

    Security:
    - Requires X-Internal-Key header matching MCP_INTERNAL_API_KEY
    - Requires X-Organization-Id header to validate organization access
    - Returns decrypted credential value

    NOTE: In production, implement proper internal API key validation.
    """
    # TODO: Validate internal API key
    # from app.core.config import settings
    # if x_internal_key != settings.MCP_INTERNAL_API_KEY:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Invalid internal API key",
    #     )

    # Fetch credential
    result = await db.execute(
        select(Credential).where(Credential.id == credential_id)
    )
    credential = result.scalar_one_or_none()

    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found",
        )

    # Validate organization if provided
    if x_organization_id and str(credential.organization_id) != x_organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Credential does not belong to the specified organization",
        )

    # Determine credential type and return appropriate format
    config_providers = [
        CredentialProvider.REDIS, CredentialProvider.POSTGRESQL, CredentialProvider.MONGODB,
        CredentialProvider.TWILIO, CredentialProvider.ETISALAT, CredentialProvider.WHATSAPP_META
    ]

    if credential.provider in config_providers:
        # Config-based credential - return parsed config
        try:
            config = json.loads(credential.api_key)
        except (json.JSONDecodeError, TypeError):
            config = credential.api_key

        return {
            "id": credential.id,
            "provider": credential.provider.value,
            "auth_type": "config",
            "config": config,
            "api_base": credential.api_base,
        }
    else:
        # API key based credential
        return {
            "id": credential.id,
            "provider": credential.provider.value,
            "auth_type": "bearer",
            "api_key": credential.api_key,  # Decrypted value
            "api_base": credential.api_base,
            "api_version": credential.api_version,
        }
