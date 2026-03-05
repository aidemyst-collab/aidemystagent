"""
MCP Servers API - Manage MCP server registry
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.models.mcp_server import MCPServer, MCPServerStatus
from app.models.tool import Tool, ToolType, ToolVisibility, ToolStatus
from app.models.user import User
from app.schemas.mcp_server import (
    MCPServerCreate,
    MCPServerUpdate,
    MCPServerResponse,
    MCPServerListResponse,
    MCPServerTestRequest,
    MCPServerTestResponse,
    MCPServerDiscoveryResponse,
    MCPServerHealthResponse,
    MCPToolSchema,
    MCPResourceSchema,
    MCPPromptSchema,
    MCPToolImportRequest,
    MCPToolImportResponse,
    ImportedToolInfo,
)
from app.api.deps import (
    get_current_active_user,
    require_permission,
    get_effective_organization_id,
)
from app.services.mcp_discovery import mcp_discovery_service


router = APIRouter()


@router.get("", response_model=MCPServerListResponse)
async def list_mcp_servers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:read")),
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
):
    """
    List all MCP servers for the organization.

    Query params:
    - skip: Number of records to skip (pagination)
    - limit: Maximum records to return
    - status_filter: Filter by status (active, inactive, error)
    """
    # Build query
    conditions = [MCPServer.organization_id == effective_org_id]

    if status_filter:
        conditions.append(MCPServer.status == status_filter)

    query = (
        select(MCPServer)
        .where(*conditions)
        .order_by(MCPServer.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    servers = result.scalars().all()

    # Get total count
    count_query = select(func.count(MCPServer.id)).where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    return MCPServerListResponse(servers=servers, total=total)


@router.get("/{server_id}", response_model=MCPServerResponse)
async def get_mcp_server(
    server_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:read")),
):
    """Get an MCP server by ID."""
    result = await db.execute(
        select(MCPServer).where(MCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP server not found",
        )

    # Check access permissions
    if server.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this MCP server",
        )

    return server


@router.post("", response_model=MCPServerResponse, status_code=status.HTTP_201_CREATED)
async def create_mcp_server(
    server_data: MCPServerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:create")),
):
    """
    Register a new MCP server.

    The server will be added with 'active' status. Use the test endpoint
    to verify connectivity before relying on it.
    """
    # Check if server name already exists for this org
    existing = await db.execute(
        select(MCPServer).where(
            MCPServer.organization_id == effective_org_id,
            MCPServer.name == server_data.name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An MCP server with this name already exists",
        )

    # Create new server
    new_server = MCPServer(
        organization_id=effective_org_id,
        creator_id=current_user.id,
        name=server_data.name,
        description=server_data.description,
        server_url=server_data.server_url,
        transport_type=server_data.transport_type,
        credential_id=server_data.credential_id,
        status=MCPServerStatus.ACTIVE,
        discovered_tools=[],
        discovered_resources=[],
        discovered_prompts=[],
    )

    db.add(new_server)
    await db.commit()
    await db.refresh(new_server)

    return new_server


@router.patch("/{server_id}", response_model=MCPServerResponse)
async def update_mcp_server(
    server_id: UUID,
    server_data: MCPServerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:update")),
):
    """Update an MCP server."""
    result = await db.execute(
        select(MCPServer).where(MCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP server not found",
        )

    # Check access permissions
    if server.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this MCP server",
        )

    # Update fields
    update_data = server_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(server, field, value)

    await db.commit()
    await db.refresh(server)

    return server


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mcp_server(
    server_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:delete")),
):
    """Delete an MCP server."""
    result = await db.execute(
        select(MCPServer).where(MCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP server not found",
        )

    # Check access permissions
    if server.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this MCP server",
        )

    await db.delete(server)
    await db.commit()

    return None


@router.post("/{server_id}/test", response_model=MCPServerTestResponse)
async def test_mcp_server(
    server_id: UUID,
    request: MCPServerTestRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:execute")),
):
    """
    Test connection to an MCP server.

    Optionally override the server URL or auth token for testing.
    """
    result = await db.execute(
        select(MCPServer).where(MCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP server not found",
        )

    # Check access permissions
    if server.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this MCP server",
        )

    # Use override values if provided
    server_url = request.server_url if request and request.server_url else server.server_url
    auth_token = request.auth_token if request and request.auth_token else None

    # TODO: Get auth token from credential if credential_id is set
    # if server.credential_id and not auth_token:
    #     credential = await get_credential(server.credential_id)
    #     auth_token = credential.api_key

    # Test connection
    health_result = await mcp_discovery_service.test_connection(
        server_url=server_url,
        auth_token=auth_token
    )

    # Update server status based on test result
    if health_result.success:
        server.status = MCPServerStatus.ACTIVE
        server.last_error = None
    else:
        server.status = MCPServerStatus.ERROR
        server.last_error = health_result.error

    server.last_health_check = datetime.utcnow()
    await db.commit()

    return MCPServerTestResponse(
        success=health_result.success,
        message="Connection successful" if health_result.success else "Connection failed",
        response_time_ms=health_result.response_time_ms,
        server_info=health_result.server_info,
        error=health_result.error,
    )


@router.post("/{server_id}/discover", response_model=MCPServerDiscoveryResponse)
async def discover_mcp_server_capabilities(
    server_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:execute")),
):
    """
    Discover tools, resources, and prompts from an MCP server.

    This will update the server's discovered_tools, discovered_resources,
    and discovered_prompts fields.
    """
    result = await db.execute(
        select(MCPServer).where(MCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP server not found",
        )

    # Check access permissions
    if server.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this MCP server",
        )

    # TODO: Get auth token from credential if credential_id is set
    auth_token = None

    # Discover capabilities
    discovery_result = await mcp_discovery_service.discover_capabilities(
        server_url=server.server_url,
        auth_token=auth_token
    )

    # Update server with discovered capabilities
    if discovery_result.success:
        server.discovered_tools = discovery_result.tools
        server.discovered_resources = discovery_result.resources
        server.discovered_prompts = discovery_result.prompts
        server.status = MCPServerStatus.ACTIVE
        server.last_error = None
    else:
        server.status = MCPServerStatus.ERROR
        server.last_error = discovery_result.error

    server.last_health_check = datetime.utcnow()
    await db.commit()

    # Convert to response schema
    tools = [MCPToolSchema(**t) for t in discovery_result.tools]
    resources = [MCPResourceSchema(**r) for r in discovery_result.resources]
    prompts = [MCPPromptSchema(**p) for p in discovery_result.prompts]

    return MCPServerDiscoveryResponse(
        success=discovery_result.success,
        tools=tools,
        resources=resources,
        prompts=prompts,
        error=discovery_result.error,
    )


@router.get("/{server_id}/health", response_model=MCPServerHealthResponse)
async def get_mcp_server_health(
    server_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:read")),
):
    """
    Get the health status of an MCP server.

    Returns the current status and last health check time without
    performing a new health check.
    """
    result = await db.execute(
        select(MCPServer).where(MCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP server not found",
        )

    # Check access permissions
    if server.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this MCP server",
        )

    return MCPServerHealthResponse(
        server_id=server.id,
        status=server.status,
        last_check=server.last_health_check or server.created_at,
        error=server.last_error,
    )


@router.post("/{server_id}/import-tools", response_model=MCPToolImportResponse)
async def import_mcp_tools(
    server_id: UUID,
    request: MCPToolImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:create")),
):
    """
    Import discovered tools from an MCP server as workflow tools.

    This creates Tool records with type='mcp' that can be used in workflows.
    The tools will reference the MCP server and use mcp_service for execution.
    """
    # Get the MCP server
    result = await db.execute(
        select(MCPServer).where(MCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MCP server not found",
        )

    # Check access permissions
    if server.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this MCP server",
        )

    # Check if server has discovered tools
    if not server.discovered_tools:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No discovered tools available. Run discovery first.",
        )

    # Build a map of discovered tools by name
    discovered_map = {tool["name"]: tool for tool in server.discovered_tools}

    imported_tools = []
    skipped_tools = []

    for tool_name in request.tool_names:
        # Check if tool exists in discovered tools
        if tool_name not in discovered_map:
            skipped_tools.append(f"{tool_name} (not found in discovered tools)")
            continue

        discovered_tool = discovered_map[tool_name]

        # Check if a tool with this name already exists for this org
        existing = await db.execute(
            select(Tool).where(
                Tool.organization_id == effective_org_id,
                Tool.name == tool_name,
            )
        )
        if existing.scalar_one_or_none():
            skipped_tools.append(f"{tool_name} (already exists)")
            continue

        # Create the Tool record
        tool_config = {
            "mcp_server_id": str(server.id),
            "mcp_server_url": server.server_url,
            "mcp_server_name": server.name,
            "mcp_type": "tool",
            "resource_uri": tool_name,
            "input_schema": discovered_tool.get("input_schema", {}),
        }

        new_tool = Tool(
            organization_id=effective_org_id,
            creator_id=current_user.id,
            name=tool_name,
            description=discovered_tool.get("description") or f"MCP tool from {server.name}",
            type=ToolType.MCP,
            config=tool_config,
            visibility=ToolVisibility.ORGANIZATION,
            status=ToolStatus.ACTIVE,
        )

        db.add(new_tool)
        await db.flush()  # Get the ID

        imported_tools.append(ImportedToolInfo(
            id=new_tool.id,
            name=new_tool.name,
            description=new_tool.description,
        ))

    await db.commit()

    return MCPToolImportResponse(
        success=True,
        imported_count=len(imported_tools),
        skipped_count=len(skipped_tools),
        imported_tools=imported_tools,
        skipped_tools=skipped_tools,
    )
