from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import Dict, Any
from uuid import UUID

from app.core.database import get_db
from app.models.version import AgentVersion
from app.models.agent import Agent
from app.models.user import User
from app.schemas.version import (
    VersionCreate,
    VersionResponse,
    VersionList,
    VersionCompare,
)
from app.api.deps import get_current_active_user, require_permission

router = APIRouter()


@router.post("/agents/{agent_id}/versions", response_model=VersionResponse, status_code=status.HTTP_201_CREATED)
async def create_version(
    agent_id: UUID,
    version: VersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("agents:update")),
):
    """Create a new version for an agent."""
    # Verify agent exists
    result = await db.execute(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.deleted_at.is_(None),
        )
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Check organization access
    if agent.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this agent",
        )

    # Get the next version number
    count_result = await db.execute(
        select(func.max(AgentVersion.version_number)).where(
            AgentVersion.agent_id == agent_id
        )
    )
    max_version = count_result.scalar()
    next_version = (max_version or 0) + 1

    # Create version
    db_version = AgentVersion(
        agent_id=agent_id,
        version_number=next_version,
        version_tag=version.version_tag,
        config=version.config,
        description=version.description,
        changelog=version.changelog,
        created_by=current_user.id,
    )

    db.add(db_version)

    # Update agent's current version number
    agent.version = next_version
    agent.config = version.config

    await db.commit()
    await db.refresh(db_version)

    return db_version


@router.get("/agents/{agent_id}/versions", response_model=VersionList)
async def list_versions(
    agent_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("agents:read")),
):
    """List all versions for an agent."""
    # Verify agent exists
    result = await db.execute(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.deleted_at.is_(None),
        )
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Check organization access
    if agent.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this agent",
        )

    # Get versions
    query = (
        select(AgentVersion)
        .where(AgentVersion.agent_id == agent_id)
        .order_by(desc(AgentVersion.version_number))
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    versions = result.scalars().all()

    # Get total count
    count_result = await db.execute(
        select(func.count(AgentVersion.id)).where(AgentVersion.agent_id == agent_id)
    )
    total = count_result.scalar() or 0

    return VersionList(versions=versions, total=total)


@router.get("/agents/{agent_id}/versions/{version_number}", response_model=VersionResponse)
async def get_version(
    agent_id: UUID,
    version_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("agents:read")),
):
    """Get a specific version of an agent."""
    # First check agent access
    agent_result = await db.execute(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.deleted_at.is_(None),
        )
    )
    agent = agent_result.scalar_one_or_none()

    if not agent or agent.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this agent",
        )

    result = await db.execute(
        select(AgentVersion).where(
            AgentVersion.agent_id == agent_id,
            AgentVersion.version_number == version_number,
        )
    )
    version = result.scalar_one_or_none()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found",
        )

    return version


@router.post("/agents/{agent_id}/versions/{version_number}/restore", response_model=VersionResponse)
async def restore_version(
    agent_id: UUID,
    version_number: int,
    description: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("agents:update")),
):
    """Restore an agent to a previous version."""
    # Get the agent first to check access
    agent_result = await db.execute(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.deleted_at.is_(None),
        )
    )
    agent = agent_result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Check organization access
    if agent.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this agent",
        )

    # Get the version to restore
    result = await db.execute(
        select(AgentVersion).where(
            AgentVersion.agent_id == agent_id,
            AgentVersion.version_number == version_number,
        )
    )
    old_version = result.scalar_one_or_none()

    if not old_version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found",
        )

    # Create a new version with the old config
    count_result = await db.execute(
        select(func.max(AgentVersion.version_number)).where(
            AgentVersion.agent_id == agent_id
        )
    )
    max_version = count_result.scalar()
    next_version = (max_version or 0) + 1

    changelog = f"Restored from version {version_number}"
    if old_version.version_tag:
        changelog += f" ({old_version.version_tag})"

    db_version = AgentVersion(
        agent_id=agent_id,
        version_number=next_version,
        version_tag=f"restored-v{version_number}",
        config=old_version.config,
        description=description or f"Restored version {version_number}",
        changelog=changelog,
        created_by=current_user.id,
    )

    db.add(db_version)

    # Update agent
    agent.version = next_version
    agent.config = old_version.config

    await db.commit()
    await db.refresh(db_version)

    return db_version


@router.get("/agents/{agent_id}/versions/compare/{version1}/{version2}", response_model=Dict[str, Any])
async def compare_versions(
    agent_id: UUID,
    version1: int,
    version2: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("agents:read")),
):
    """Compare two versions of an agent."""
    # Get both versions
    result1 = await db.execute(
        select(AgentVersion).where(
            AgentVersion.agent_id == agent_id,
            AgentVersion.version_number == version1,
        )
    )
    v1 = result1.scalar_one_or_none()

    result2 = await db.execute(
        select(AgentVersion).where(
            AgentVersion.agent_id == agent_id,
            AgentVersion.version_number == version2,
        )
    )
    v2 = result2.scalar_one_or_none()

    if not v1 or not v2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or both versions not found",
        )

    # Simple diff (in production, use a proper diff library)
    differences = {
        "nodes_added": [],
        "nodes_removed": [],
        "nodes_modified": [],
        "edges_added": [],
        "edges_removed": [],
    }

    v1_node_ids = {n["id"] for n in v1.config.get("nodes", [])}
    v2_node_ids = {n["id"] for n in v2.config.get("nodes", [])}

    differences["nodes_added"] = list(v2_node_ids - v1_node_ids)
    differences["nodes_removed"] = list(v1_node_ids - v2_node_ids)

    v1_edge_ids = {
        f"{e['source']}-{e['target']}" for e in v1.config.get("edges", [])
    }
    v2_edge_ids = {
        f"{e['source']}-{e['target']}" for e in v2.config.get("edges", [])
    }

    differences["edges_added"] = list(v2_edge_ids - v1_edge_ids)
    differences["edges_removed"] = list(v1_edge_ids - v2_edge_ids)

    return {
        "version1": v1,
        "version2": v2,
        "differences": differences,
    }


@router.delete("/agents/{agent_id}/versions/{version_number}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_version(
    agent_id: UUID,
    version_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("agents:delete")),
):
    """Delete a specific version (not recommended for production)."""
    # Check agent access first
    agent_result = await db.execute(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.deleted_at.is_(None),
        )
    )
    agent = agent_result.scalar_one_or_none()

    if not agent or agent.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this agent",
        )

    result = await db.execute(
        select(AgentVersion).where(
            AgentVersion.agent_id == agent_id,
            AgentVersion.version_number == version_number,
        )
    )
    version = result.scalar_one_or_none()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found",
        )

    await db.delete(version)
    await db.commit()
