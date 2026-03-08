"""
Dynamic MCP Servers API - Manage API-based MCP Servers with Tools

Each server groups multiple tools that share the same base URL and credentials.
Users create servers via UI, and the Dynamic MCP Server runtime exposes them as MCP tools.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
from uuid import UUID
import httpx

from app.core.database import get_db
from app.core.config import settings
from app.models.dynamic_mcp_server import DynamicMCPServer
from app.models.dynamic_mcp_tool import DynamicMCPTool
from app.models.user import User
from app.models.credential import Credential
from app.schemas.dynamic_mcp import (
    DynamicMCPServerCreate,
    DynamicMCPServerUpdate,
    DynamicMCPServerResponse,
    DynamicMCPServerListResponse,
    DynamicMCPToolCreate,
    DynamicMCPToolUpdate,
    DynamicMCPToolResponse,
    DynamicMCPServersInternalResponse,
    ToolExecuteRequest,
    ToolExecuteResponse,
)
from app.api.deps import (
    get_current_active_user,
    require_permission,
    get_effective_organization_id,
)


router = APIRouter()


# ==============================================================================
# Helper Functions
# ==============================================================================

def _server_to_response(server: DynamicMCPServer) -> dict:
    """Convert server model to response dict with computed properties."""
    return {
        "id": server.id,
        "organization_id": server.organization_id,
        "creator_id": server.creator_id,
        "name": server.name,
        "description": server.description,
        "base_url": server.base_url,
        "credential_id": server.credential_id,
        "default_headers": server.default_headers or {},
        "timeout_seconds": server.timeout_seconds,
        "is_active": server.is_active,
        "tools": server.tools or [],
        "tool_count": len(server.tools) if server.tools else 0,
        "active_tool_count": sum(1 for t in (server.tools or []) if t.is_active),
        "created_at": server.created_at,
        "updated_at": server.updated_at,
    }


# ==============================================================================
# Server CRUD Endpoints
# ==============================================================================

@router.get("", response_model=DynamicMCPServerListResponse)
async def list_dynamic_mcp_servers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:read")),
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
):
    """
    List all Dynamic MCP Servers for the organization.

    Each server contains multiple tools that share the same base URL and credentials.

    Query params:
    - skip: Number of records to skip (pagination)
    - limit: Maximum records to return
    - active_only: Only return active servers (default: false)
    """
    conditions = [DynamicMCPServer.organization_id == effective_org_id]

    if active_only:
        conditions.append(DynamicMCPServer.is_active == True)

    query = (
        select(DynamicMCPServer)
        .options(selectinload(DynamicMCPServer.tools))
        .where(*conditions)
        .order_by(DynamicMCPServer.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    servers = result.scalars().unique().all()

    # Get total count
    count_query = select(func.count(DynamicMCPServer.id)).where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    return {
        "servers": [_server_to_response(s) for s in servers],
        "total": total,
    }


@router.get("/{server_id}", response_model=DynamicMCPServerResponse)
async def get_dynamic_mcp_server(
    server_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:read")),
):
    """Get a Dynamic MCP Server by ID with all its tools."""
    result = await db.execute(
        select(DynamicMCPServer)
        .options(selectinload(DynamicMCPServer.tools))
        .where(DynamicMCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dynamic MCP Server not found",
        )

    if server.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this server",
        )

    return _server_to_response(server)


@router.post("", response_model=DynamicMCPServerResponse, status_code=status.HTTP_201_CREATED)
async def create_dynamic_mcp_server(
    server_data: DynamicMCPServerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:create")),
):
    """
    Create a new Dynamic MCP Server with optional initial tools.

    Example:
    {
        "name": "Weather API",
        "base_url": "https://api.openweathermap.org/data/2.5",
        "credential_id": "cred-uuid",
        "tools": [
            {
                "name": "get_current_weather",
                "description": "Get current weather for a city",
                "path": "/weather",
                "method": "GET",
                "parameters": [
                    {"name": "q", "type": "string", "required": true}
                ]
            }
        ]
    }
    """
    # Check if server name already exists for this org
    existing = await db.execute(
        select(DynamicMCPServer).where(
            DynamicMCPServer.organization_id == effective_org_id,
            DynamicMCPServer.name == server_data.name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A server with this name already exists",
        )

    # Validate credential if provided
    if server_data.credential_id:
        cred_result = await db.execute(
            select(Credential).where(Credential.id == server_data.credential_id)
        )
        credential = cred_result.scalar_one_or_none()
        if not credential:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credential not found",
            )

    # Create server
    new_server = DynamicMCPServer(
        organization_id=effective_org_id,
        creator_id=current_user.id,
        name=server_data.name,
        description=server_data.description,
        base_url=server_data.base_url,
        credential_id=server_data.credential_id,
        default_headers=server_data.default_headers or {},
        timeout_seconds=server_data.timeout_seconds,
        is_active=True,
    )
    db.add(new_server)
    await db.flush()  # Get the server ID

    # Create initial tools if provided
    if server_data.tools:
        for tool_data in server_data.tools:
            # Check for duplicate tool names within server
            tool_names = [t.name for t in server_data.tools]
            if tool_names.count(tool_data.name) > 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate tool name: {tool_data.name}",
                )

            parameters = [p.model_dump() for p in tool_data.parameters] if tool_data.parameters else []

            new_tool = DynamicMCPTool(
                server_id=new_server.id,
                name=tool_data.name,
                description=tool_data.description,
                path=tool_data.path,
                method=tool_data.method.value,
                parameters=parameters,
                headers=tool_data.headers or {},
                query_params=tool_data.query_params or {},
                body_template=tool_data.body_template or {},
                response_path=tool_data.response_path,
                is_active=True,
            )
            db.add(new_tool)

    await db.commit()

    # Reload with tools
    result = await db.execute(
        select(DynamicMCPServer)
        .options(selectinload(DynamicMCPServer.tools))
        .where(DynamicMCPServer.id == new_server.id)
    )
    server = result.scalar_one()

    return _server_to_response(server)


@router.patch("/{server_id}", response_model=DynamicMCPServerResponse)
async def update_dynamic_mcp_server(
    server_id: UUID,
    server_data: DynamicMCPServerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:update")),
):
    """Update a Dynamic MCP Server's configuration."""
    result = await db.execute(
        select(DynamicMCPServer)
        .options(selectinload(DynamicMCPServer.tools))
        .where(DynamicMCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dynamic MCP Server not found",
        )

    if server.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this server",
        )

    # Check name uniqueness if changing name
    if server_data.name and server_data.name != server.name:
        existing = await db.execute(
            select(DynamicMCPServer).where(
                DynamicMCPServer.organization_id == effective_org_id,
                DynamicMCPServer.name == server_data.name,
                DynamicMCPServer.id != server_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A server with this name already exists",
            )

    # Update fields
    update_data = server_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(server, field, value)

    await db.commit()
    await db.refresh(server)

    return _server_to_response(server)


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dynamic_mcp_server(
    server_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:delete")),
):
    """
    Delete a Dynamic MCP Server and all its tools.

    This is a permanent deletion. All tools within the server will be deleted.
    """
    result = await db.execute(
        select(DynamicMCPServer).where(DynamicMCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dynamic MCP Server not found",
        )

    if server.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this server",
        )

    await db.delete(server)  # Cascade deletes tools
    await db.commit()

    return None


@router.post("/{server_id}/toggle", response_model=DynamicMCPServerResponse)
async def toggle_dynamic_mcp_server(
    server_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:update")),
):
    """Toggle a Dynamic MCP Server's active status."""
    result = await db.execute(
        select(DynamicMCPServer)
        .options(selectinload(DynamicMCPServer.tools))
        .where(DynamicMCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dynamic MCP Server not found",
        )

    if server.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this server",
        )

    server.is_active = not server.is_active
    await db.commit()
    await db.refresh(server)

    return _server_to_response(server)


# ==============================================================================
# Tool CRUD Endpoints (within a server)
# ==============================================================================

@router.post("/{server_id}/tools", response_model=DynamicMCPToolResponse, status_code=status.HTTP_201_CREATED)
async def add_tool_to_server(
    server_id: UUID,
    tool_data: DynamicMCPToolCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:create")),
):
    """Add a new tool to a Dynamic MCP Server."""
    # Get and validate server
    result = await db.execute(
        select(DynamicMCPServer)
        .options(selectinload(DynamicMCPServer.tools))
        .where(DynamicMCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dynamic MCP Server not found",
        )

    if server.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this server",
        )

    # Check for duplicate tool name within server
    existing_tool = await db.execute(
        select(DynamicMCPTool).where(
            DynamicMCPTool.server_id == server_id,
            DynamicMCPTool.name == tool_data.name,
        )
    )
    if existing_tool.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A tool with this name already exists in this server",
        )

    # Create tool
    parameters = [p.model_dump() for p in tool_data.parameters] if tool_data.parameters else []

    new_tool = DynamicMCPTool(
        server_id=server_id,
        name=tool_data.name,
        description=tool_data.description,
        path=tool_data.path,
        method=tool_data.method.value,
        parameters=parameters,
        headers=tool_data.headers or {},
        query_params=tool_data.query_params or {},
        body_template=tool_data.body_template or {},
        response_path=tool_data.response_path,
        is_active=True,
    )

    db.add(new_tool)
    await db.commit()
    await db.refresh(new_tool)

    return new_tool


@router.patch("/{server_id}/tools/{tool_id}", response_model=DynamicMCPToolResponse)
async def update_tool_in_server(
    server_id: UUID,
    tool_id: UUID,
    tool_data: DynamicMCPToolUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:update")),
):
    """Update a tool within a Dynamic MCP Server."""
    # Validate server access
    server_result = await db.execute(
        select(DynamicMCPServer).where(DynamicMCPServer.id == server_id)
    )
    server = server_result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dynamic MCP Server not found",
        )

    if server.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this server",
        )

    # Get tool
    result = await db.execute(
        select(DynamicMCPTool).where(
            DynamicMCPTool.id == tool_id,
            DynamicMCPTool.server_id == server_id,
        )
    )
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found in this server",
        )

    # Check name uniqueness if changing
    if tool_data.name and tool_data.name != tool.name:
        existing = await db.execute(
            select(DynamicMCPTool).where(
                DynamicMCPTool.server_id == server_id,
                DynamicMCPTool.name == tool_data.name,
                DynamicMCPTool.id != tool_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A tool with this name already exists in this server",
            )

    # Update fields
    update_data = tool_data.model_dump(exclude_unset=True)

    # Handle method enum
    if 'method' in update_data and update_data['method']:
        update_data['method'] = update_data['method'].value

    # Handle parameters
    if 'parameters' in update_data and update_data['parameters']:
        update_data['parameters'] = [
            p.model_dump() if hasattr(p, 'model_dump') else p
            for p in update_data['parameters']
        ]

    for field, value in update_data.items():
        setattr(tool, field, value)

    await db.commit()
    await db.refresh(tool)

    return tool


@router.delete("/{server_id}/tools/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool_from_server(
    server_id: UUID,
    tool_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:delete")),
):
    """Delete a tool from a Dynamic MCP Server."""
    # Validate server access
    server_result = await db.execute(
        select(DynamicMCPServer).where(DynamicMCPServer.id == server_id)
    )
    server = server_result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dynamic MCP Server not found",
        )

    if server.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this server",
        )

    # Get and delete tool
    result = await db.execute(
        select(DynamicMCPTool).where(
            DynamicMCPTool.id == tool_id,
            DynamicMCPTool.server_id == server_id,
        )
    )
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found in this server",
        )

    await db.delete(tool)
    await db.commit()

    return None


@router.post("/{server_id}/tools/{tool_id}/toggle", response_model=DynamicMCPToolResponse)
async def toggle_tool_in_server(
    server_id: UUID,
    tool_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:update")),
):
    """Toggle a tool's active status within a server."""
    # Validate server access
    server_result = await db.execute(
        select(DynamicMCPServer).where(DynamicMCPServer.id == server_id)
    )
    server = server_result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dynamic MCP Server not found",
        )

    if server.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this server",
        )

    # Get tool
    result = await db.execute(
        select(DynamicMCPTool).where(
            DynamicMCPTool.id == tool_id,
            DynamicMCPTool.server_id == server_id,
        )
    )
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found in this server",
        )

    tool.is_active = not tool.is_active
    await db.commit()
    await db.refresh(tool)

    return tool


# ==============================================================================
# Test Tool Execution
# ==============================================================================

@router.post("/{server_id}/tools/{tool_id}/test", response_model=ToolExecuteResponse)
async def test_tool_execution(
    server_id: UUID,
    tool_id: UUID,
    request: ToolExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:execute")),
):
    """
    Test execute a tool with provided arguments.

    This makes the actual API call using the server's configuration.
    """
    import time
    import json

    start_time = time.time()

    # Get server with credential
    server_result = await db.execute(
        select(DynamicMCPServer).where(DynamicMCPServer.id == server_id)
    )
    server = server_result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dynamic MCP Server not found",
        )

    if server.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this server",
        )

    # Get tool
    tool_result = await db.execute(
        select(DynamicMCPTool).where(
            DynamicMCPTool.id == tool_id,
            DynamicMCPTool.server_id == server_id,
        )
    )
    tool = tool_result.scalar_one_or_none()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found",
        )

    try:
        # Build full URL
        full_url = tool.get_full_url(server.base_url)

        # Replace path parameters
        for key, value in request.arguments.items():
            full_url = full_url.replace(f"{{{key}}}", str(value))

        # Build headers
        headers = dict(server.default_headers or {})
        headers.update(tool.headers or {})
        headers.setdefault("Content-Type", "application/json")

        # Add authentication if credential exists
        if server.credential_id:
            cred_result = await db.execute(
                select(Credential).where(Credential.id == server.credential_id)
            )
            credential = cred_result.scalar_one_or_none()
            if credential:
                # Get decrypted value
                api_key = credential.decrypted_value
                if isinstance(api_key, dict):
                    api_key = api_key.get('api_key', api_key.get('auth_token', ''))
                headers["Authorization"] = f"Bearer {api_key}"

        # Build query params
        query_params = dict(tool.query_params or {})
        if tool.method.upper() == "GET":
            query_params.update(request.arguments)

        # Build body
        body = None
        if tool.method.upper() in ["POST", "PUT", "PATCH"]:
            if tool.body_template:
                body = dict(tool.body_template)
                body.update(request.arguments)
            else:
                body = request.arguments

        # Make request
        async with httpx.AsyncClient(timeout=float(server.timeout_seconds)) as client:
            if tool.method.upper() == "GET":
                response = await client.get(full_url, params=query_params, headers=headers)
            elif tool.method.upper() == "POST":
                response = await client.post(full_url, json=body, params=query_params, headers=headers)
            elif tool.method.upper() == "PUT":
                response = await client.put(full_url, json=body, params=query_params, headers=headers)
            elif tool.method.upper() == "PATCH":
                response = await client.patch(full_url, json=body, params=query_params, headers=headers)
            elif tool.method.upper() == "DELETE":
                response = await client.delete(full_url, params=query_params, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {tool.method}")

            # Parse response
            try:
                result = response.json()

                # Extract path if configured
                if tool.response_path:
                    for part in tool.response_path.split("."):
                        if isinstance(result, dict) and part in result:
                            result = result[part]
                        elif isinstance(result, list) and part.isdigit():
                            result = result[int(part)]
                        else:
                            break

            except json.JSONDecodeError:
                result = response.text

            execution_time = int((time.time() - start_time) * 1000)

            return ToolExecuteResponse(
                success=response.status_code < 400,
                result=result,
                error=None if response.status_code < 400 else f"HTTP {response.status_code}",
                execution_time_ms=execution_time,
            )

    except httpx.TimeoutException:
        return ToolExecuteResponse(
            success=False,
            result=None,
            error=f"Request timed out after {server.timeout_seconds} seconds",
            execution_time_ms=int((time.time() - start_time) * 1000),
        )
    except Exception as e:
        return ToolExecuteResponse(
            success=False,
            result=None,
            error=str(e),
            execution_time_ms=int((time.time() - start_time) * 1000),
        )


# ==============================================================================
# Internal API for Dynamic MCP Server Runtime
# ==============================================================================

@router.get("/internal/all", response_model=DynamicMCPServersInternalResponse)
async def get_all_servers_internal(
    db: AsyncSession = Depends(get_db),
    x_internal_key: Optional[str] = Header(None, alias="X-Internal-Key"),
):
    """
    Internal endpoint for Dynamic MCP Server runtime to fetch all server and tool definitions.

    This endpoint is called by the Dynamic MCP Server at startup and periodically.
    Returns all active servers with their active tools in execution-ready format.

    Protected by internal API key.
    """
    # Validate internal key
    expected_key = getattr(settings, 'MCP_INTERNAL_API_KEY', None)
    if expected_key and x_internal_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal API key",
        )

    # Get all active servers with active tools
    query = (
        select(DynamicMCPServer)
        .options(selectinload(DynamicMCPServer.tools))
        .where(DynamicMCPServer.is_active == True)
    )
    result = await db.execute(query)
    servers = result.scalars().unique().all()

    # Convert to internal format
    servers_data = []
    for server in servers:
        server_data = {
            "id": str(server.id),
            "name": server.name,
            "description": server.description,
            "base_url": server.base_url,
            "credential_id": server.credential_id,
            "organization_id": str(server.organization_id),
            "default_headers": server.default_headers or {},
            "timeout_seconds": server.timeout_seconds,
            "is_active": server.is_active,
            "tools": [
                tool.to_mcp_tool_schema()
                for tool in (server.tools or [])
                if tool.is_active
            ],
        }
        servers_data.append(server_data)

    return {
        "servers": servers_data,
        "total": len(servers_data),
    }
