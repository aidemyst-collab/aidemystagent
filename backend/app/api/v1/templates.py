from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.agent import Agent, AgentStatus
from app.services.templates import AgentTemplates

router = APIRouter()


@router.get("/")
async def list_templates():
    """List all available agent templates."""
    templates = AgentTemplates.get_all_templates()
    return {"templates": templates}


@router.get("/{template_id}")
async def get_template(template_id: str):
    """Get a specific template by ID."""
    templates = AgentTemplates.get_all_templates()
    template = next((t for t in templates if t["id"] == template_id), None)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    return template


@router.post("/{template_id}/clone")
async def clone_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Clone a template to create a new agent."""
    templates = AgentTemplates.get_all_templates()
    template = next((t for t in templates if t["id"] == template_id), None)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # TODO: Get current user from auth
    org_id = "00000000-0000-0000-0000-000000000000"
    creator_id = "00000000-0000-0000-0000-000000000000"

    # Create new agent from template
    agent = Agent(
        name=template["name"],
        description=template["description"],
        config=template["config"],
        organization_id=org_id,
        creator_id=creator_id,
        status=AgentStatus.DRAFT,
    )

    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    return {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "message": "Template cloned successfully",
    }
