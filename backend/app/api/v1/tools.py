from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.tool import Tool

router = APIRouter()


@router.get("/")
async def list_tools(db: AsyncSession = Depends(get_db)):
    """List all tools."""
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
    # TODO: Implement tool creation
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/{tool_id}/test")
async def test_tool(tool_id: UUID, db: AsyncSession = Depends(get_db)):
    """Test a tool."""
    # TODO: Implement tool testing
    return {"message": "Tool test endpoint - not yet implemented"}


@router.get("/categories")
async def list_tool_categories():
    """List tool categories."""
    return {
        "categories": [
            "Built-in",
            "API Integration",
            "Custom",
        ]
    }
