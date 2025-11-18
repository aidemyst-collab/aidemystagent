from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any
from uuid import UUID
from pydantic import BaseModel

from app.core.database import get_db
from app.models.tool import Tool
from app.services.tools import tool_registry


router = APIRouter()


class ToolExecuteRequest(BaseModel):
    """Request model for tool execution."""
    input_data: Dict[str, Any]


@router.get("/built-in")
async def list_builtin_tools():
    """List all built-in tools."""
    tools = tool_registry.list_tools()
    return {"tools": tools}


@router.post("/built-in/{tool_name}/execute")
async def execute_builtin_tool(tool_name: str, request: ToolExecuteRequest):
    """Execute a built-in tool."""
    result = await tool_registry.execute_tool(tool_name, request.input_data)
    return result


@router.get("/")
async def list_tools(db: AsyncSession = Depends(get_db)):
    """List all custom tools from database."""
    result = await db.execute(select(Tool))
    tools = result.scalars().all()
    return {"tools": tools}


@router.get("/{tool_id}")
async def get_tool(tool_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get tool by ID."""
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found",
        )

    return tool


@router.post("/")
async def create_tool(db: AsyncSession = Depends(get_db)):
    """Create a custom tool."""
    # TODO: Implement custom tool creation
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/{tool_id}/test")
async def test_tool(tool_id: UUID, request: ToolExecuteRequest, db: AsyncSession = Depends(get_db)):
    """Test a custom tool."""
    result = await db.execute(select(Tool).where(Tool.id == tool_id))
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool not found",
        )

    # TODO: Execute custom tool
    return {"message": "Custom tool execution not yet implemented"}


@router.get("/categories/list")
async def list_tool_categories():
    """List tool categories."""
    return {
        "categories": [
            {
                "name": "Built-in",
                "description": "Pre-built tools for common operations",
                "tools": ["calculator", "datetime", "json_parser", "web_search"]
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
