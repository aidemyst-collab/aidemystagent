from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.models.tool import Tool
from app.models.user import User
from app.services.tools import tool_registry, APIIntegrationTool
from app.schemas.tool import (
    ToolCreate,
    ToolUpdate,
    ToolResponse,
    ToolListResponse,
    ToolExecuteRequest,
    ToolExecuteResponse,
)
from app.api.deps import (
    get_current_active_user,
    get_permission_service,
    require_permission,
)
from app.services.permission_service import PermissionService


router = APIRouter()


@router.get("/built-in")
async def list_builtin_tools(
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("tools:read")),
):
    """List all built-in tools."""
    tools = tool_registry.list_tools()
    return {"tools": tools}


@router.post("/built-in/{tool_name}/execute")
async def execute_builtin_tool(
    tool_name: str,
    request: ToolExecuteRequest,
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("tools:read")),
):
    """Execute a built-in tool."""
    result = await tool_registry.execute_tool(tool_name, request.input_data)
    return result


@router.get("/", response_model=ToolListResponse)
async def list_tools(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("tools:read")),
    skip: int = 0,
    limit: int = 100,
    tool_type: str = None,
):
    """List all custom tools from database, optionally filtered by type."""
    # Build base query for tools the user has access to
    base_conditions = [
        (Tool.creator_id == current_user.id) |
        (Tool.organization_id == current_user.organization_id) |
        (Tool.visibility == "public")
    ]

    # Add type filter if provided
    if tool_type:
        base_conditions.append(Tool.type == tool_type)

    query = select(Tool).where(*base_conditions).offset(skip).limit(limit)
    result = await db.execute(query)
    tools = result.scalars().all()

    # Get total count
    count_query = select(func.count(Tool.id)).where(*base_conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    return ToolListResponse(tools=tools, total=total)


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("tools:read")),
):
    """Get tool by ID."""
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found",
        )

    # Check access permissions
    if (
        tool.creator_id != current_user.id
        and tool.organization_id != current_user.organization_id
        and tool.visibility != "public"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this tool",
        )

    return tool


@router.post("/", response_model=ToolResponse, status_code=status.HTTP_201_CREATED)
async def create_tool(
    tool_data: ToolCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("tools:create")),
):
    """Create a custom tool."""
    # Check if tool name already exists for this user/org
    existing_tool = await db.execute(
        select(Tool).where(
            Tool.name == tool_data.name,
            (Tool.creator_id == current_user.id) |
            (Tool.organization_id == current_user.organization_id)
        )
    )

    if existing_tool.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A tool with this name already exists",
        )

    # Create new tool
    new_tool = Tool(
        name=tool_data.name,
        description=tool_data.description,
        type=tool_data.type,
        config=tool_data.config,
        visibility=tool_data.visibility,
        status=tool_data.status,
        creator_id=current_user.id,
        organization_id=current_user.organization_id,
    )

    db.add(new_tool)
    await db.commit()
    await db.refresh(new_tool)

    return new_tool


@router.put("/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: UUID,
    tool_data: ToolUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("tools:update")),
):
    """Update a tool."""
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found",
        )

    # Only creator can update
    if tool.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the tool creator can update it",
        )

    # Update fields
    update_data = tool_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tool, field, value)

    await db.commit()
    await db.refresh(tool)

    return tool


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool(
    tool_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("tools:delete")),
):
    """Delete a tool."""
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found",
        )

    # Only creator can delete
    if tool.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the tool creator can delete it",
        )

    await db.delete(tool)
    await db.commit()

    return None


@router.post("/{tool_id}/test", response_model=ToolExecuteResponse)
async def test_tool(
    tool_id: UUID,
    request: ToolExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("tools:execute")),
):
    """Test a custom tool."""
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found",
        )

    # Check access permissions
    if (
        tool.creator_id != current_user.id
        and tool.organization_id != current_user.organization_id
        and tool.visibility != "public"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this tool",
        )

    # Execute tool based on type
    try:
        if tool.type == "custom":
            # TODO: Execute custom code in sandbox
            return ToolExecuteResponse(
                success=True,
                result={"message": "Custom code execution not yet implemented"},
                error=None,
            )
        elif tool.type == "api":
            # Execute API call using APIIntegrationTool
            api_config = tool.config.get("api", {})
            api_tool = APIIntegrationTool(
                name=tool.name,
                description=tool.description,
                endpoint=api_config.get("endpoint"),
                method=api_config.get("method", "GET"),
                auth_type=api_config.get("auth_type", "none"),
                headers=api_config.get("headers", {}),
                timeout=api_config.get("timeout", 30)
            )

            result = await api_tool.execute(request.input_data)
            return ToolExecuteResponse(
                success=result.success,
                result=result.result,
                error=result.error,
            )
        elif tool.type == "mcp":
            # TODO: Execute MCP tool
            return ToolExecuteResponse(
                success=True,
                result={"message": "MCP execution not yet implemented"},
                error=None,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown tool type: {tool.type}",
            )
    except Exception as e:
        return ToolExecuteResponse(
            success=False,
            result=None,
            error=str(e),
        )


@router.get("/categories/list")
async def list_tool_categories(
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("tools:read")),
):
    """List tool categories."""
    return {
        "categories": [
            {
                "name": "Built-in",
                "description": "Pre-built tools for common operations",
                "tools": ["calculator", "datetime", "json_parser", "web_search", "api_integration"]
            },
            {
                "name": "API Integration",
                "description": "Tools for interacting with external APIs",
                "tools": []
            },
            {
                "name": "Custom",
                "description": "User-created custom tools",
                "tools": []
            },
        ]
    }
