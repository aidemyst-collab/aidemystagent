from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.agent import Agent, AgentStatus
from app.models.user import User
from app.services.templates import AgentTemplates
from app.api.deps import get_current_active_user, require_permission

router = APIRouter()


@router.get("/")
async def list_templates(
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("agents:read")),
):
    """List all available agent templates."""
    templates = AgentTemplates.get_all_templates()
    return {"templates": templates}


@router.get("/{template_id}")
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("agents:read")),
):
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
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("agents:create")),
):
    """Clone a template to create a new agent."""
    templates = AgentTemplates.get_all_templates()
    template = next((t for t in templates if t["id"] == template_id), None)

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    # Create new agent from template
    agent = Agent(
        name=template["name"],
        description=template["description"],
        config=template["config"],
        organization_id=current_user.organization_id,
        creator_id=current_user.id,
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
