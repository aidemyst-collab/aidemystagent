"""
MCP Tools API - Manage Dynamic MCP Tool definitions

These tools are created via UI and executed by the Dynamic MCP Server.
The server reads these definitions to expose them as MCP tools.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.models.dynamic_mcp_tool import DynamicMCPTool
from app.models.user import User
from app.schemas.tool import (
    DynamicMCPToolCreate,
    DynamicMCPToolUpdate,
    DynamicMCPToolResponse,
    DynamicMCPToolListResponse,
    ToolParameter,
)
from app.api.deps import (
    get_current_active_user,
    require_permission,
    get_effective_organization_id,
)


router = APIRouter()


@router.get("", response_model=DynamicMCPToolListResponse)
async def list_dynamic_mcp_tools(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:read")),
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
):
    """
    List all Dynamic MCP tools for the organization.

    These are the tool definitions that the Dynamic MCP Server uses.

    Query params:
    - skip: Number of records to skip (pagination)
    - limit: Maximum records to return
    - active_only: Only return active tools (default: true)
    """
    conditions = [DynamicMCPTool.organization_id == effective_org_id]

    if active_only:
        conditions.append(DynamicMCPTool.is_active == True)

    query = (
        select(DynamicMCPTool)
        .where(*conditions)
        .order_by(DynamicMCPTool.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    tools = result.scalars().all()

    # Get total count
    count_query = select(func.count(DynamicMCPTool.id)).where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    return DynamicMCPToolListResponse(tools=tools, total=total)


@router.get("/schemas")
async def get_mcp_tool_schemas(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:read")),
):
    """
    Get all active tools as MCP tool schemas.

    This endpoint is used by the Dynamic MCP Server to fetch tool definitions.
    Returns tools in MCP-compatible format with inputSchema.
    """
    query = (
        select(DynamicMCPTool)
        .where(
            DynamicMCPTool.organization_id == effective_org_id,
            DynamicMCPTool.is_active == True
        )
    )
    result = await db.execute(query)
    tools = result.scalars().all()

    return {
        "tools": [tool.to_mcp_tool_schema() for tool in tools],
        "total": len(tools),
    }


@router.get("/{tool_id}", response_model=DynamicMCPToolResponse)
async def get_dynamic_mcp_tool(
    tool_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:read")),
):
    """Get a Dynamic MCP tool by ID."""
    result = await db.execute(
        select(DynamicMCPTool).where(DynamicMCPTool.id == tool_id)
    )
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dynamic MCP tool not found",
        )

    if tool.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this tool",
        )

    return tool


@router.post("", response_model=DynamicMCPToolResponse, status_code=status.HTTP_201_CREATED)
async def create_dynamic_mcp_tool(
    tool_data: DynamicMCPToolCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:create")),
):
    """
    Create a new Dynamic MCP tool.

    This defines an API-based tool that will be exposed via the Dynamic MCP Server.
    Agents can then use this tool by name, and the server will make the actual API call.
    """
    # Check if tool name already exists for this org
    existing = await db.execute(
        select(DynamicMCPTool).where(
            DynamicMCPTool.organization_id == effective_org_id,
            DynamicMCPTool.name == tool_data.name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A tool with this name already exists",
        )

    # Convert parameters to dict format
    parameters = [p.dict() for p in tool_data.parameters] if tool_data.parameters else []

    # Create new tool
    new_tool = DynamicMCPTool(
        organization_id=effective_org_id,
        creator_id=current_user.id,
        name=tool_data.name,
        description=tool_data.description,
        api_endpoint=tool_data.api_endpoint,
        method=tool_data.method.value,
        parameters=parameters,
        headers=tool_data.headers or {},
        query_params=tool_data.query_params or {},
        body_template=tool_data.body_template or {},
        credential_id=tool_data.credential_id,
        response_path=tool_data.response_path,
        response_template=tool_data.response_template,
        timeout_seconds=tool_data.timeout_seconds,
        is_active=True,
    )

    db.add(new_tool)
    await db.commit()
    await db.refresh(new_tool)

    return new_tool


@router.patch("/{tool_id}", response_model=DynamicMCPToolResponse)
async def update_dynamic_mcp_tool(
    tool_id: UUID,
    tool_data: DynamicMCPToolUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:update")),
):
    """Update a Dynamic MCP tool."""
    result = await db.execute(
        select(DynamicMCPTool).where(DynamicMCPTool.id == tool_id)
    )
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dynamic MCP tool not found",
        )

    if tool.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this tool",
        )

    # Update fields
    update_data = tool_data.dict(exclude_unset=True)

    # Handle method enum
    if 'method' in update_data and update_data['method']:
        update_data['method'] = update_data['method'].value

    # Handle parameters
    if 'parameters' in update_data and update_data['parameters']:
        update_data['parameters'] = [p.dict() if hasattr(p, 'dict') else p for p in update_data['parameters']]

    for field, value in update_data.items():
        setattr(tool, field, value)

    await db.commit()
    await db.refresh(tool)

    return tool


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dynamic_mcp_tool(
    tool_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:delete")),
):
    """Delete a Dynamic MCP tool."""
    result = await db.execute(
        select(DynamicMCPTool).where(DynamicMCPTool.id == tool_id)
    )
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dynamic MCP tool not found",
        )

    if tool.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this tool",
        )

    await db.delete(tool)
    await db.commit()

    return None


@router.post("/{tool_id}/toggle", response_model=DynamicMCPToolResponse)
async def toggle_dynamic_mcp_tool(
    tool_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:update")),
):
    """Toggle a Dynamic MCP tool's active status."""
    result = await db.execute(
        select(DynamicMCPTool).where(DynamicMCPTool.id == tool_id)
    )
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dynamic MCP tool not found",
        )

    if tool.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this tool",
        )

    tool.is_active = not tool.is_active
    await db.commit()
    await db.refresh(tool)

    return tool


@router.post("/refresh")
async def refresh_dynamic_mcp_server(
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
    _: None = Depends(require_permission("tools:update")),
):
    """
    Notify the Dynamic MCP Server to reload tool definitions.

    This is called after creating/updating/deleting tools to ensure
    the server has the latest definitions.
    """
    # TODO: Implement webhook or message queue to notify Dynamic MCP Server
    # For now, just return success - the server will poll for updates

    return {
        "success": True,
        "message": "Dynamic MCP Server will reload tools on next request",
    }


# ============================================================================
# Internal API for Dynamic MCP Server
# ============================================================================

@router.get("/internal/all")
async def get_all_tools_internal(
    db: AsyncSession = Depends(get_db),
    x_internal_key: str = None,
):
    """
    Internal endpoint for Dynamic MCP Server to fetch all tool definitions.

    This endpoint is called by the Dynamic MCP Server at startup and periodically
    to get the latest tool definitions.

    NOTE: This should be protected by an internal API key in production.
    """
    # TODO: Add internal API key validation
    # if x_internal_key != settings.MCP_INTERNAL_API_KEY:
    #     raise HTTPException(403, "Invalid internal key")

    query = select(DynamicMCPTool).where(DynamicMCPTool.is_active == True)
    result = await db.execute(query)
    tools = result.scalars().all()

    return {
        "tools": [tool.to_mcp_tool_schema() for tool in tools],
        "total": len(tools),
    }
