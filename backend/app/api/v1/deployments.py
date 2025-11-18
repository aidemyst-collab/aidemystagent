from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List
from uuid import UUID
from datetime import datetime
import secrets

from app.core.database import get_db
from app.models.deployment import Deployment, DeploymentStatus, DeploymentEnvironment
from app.models.agent import Agent
from app.schemas.deployment import (
    DeploymentCreate,
    DeploymentUpdate,
    DeploymentResponse,
    DeploymentList,
)

router = APIRouter()


@router.post("/", response_model=DeploymentResponse, status_code=status.HTTP_201_CREATED)
async def create_deployment(
    deployment: DeploymentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new deployment for an agent."""
    # Verify agent exists
    result = await db.execute(select(Agent).where(Agent.id == deployment.agent_id))
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # TODO: Get current user from auth
    user_id = "00000000-0000-0000-0000-000000000000"

    # Generate API key for the deployment
    api_key = f"sk-{secrets.token_urlsafe(32)}"

    # Generate endpoint URL
    endpoint_url = f"/api/v1/deployments/{deployment.agent_id}/invoke"

    # Create deployment
    db_deployment = Deployment(
        agent_id=deployment.agent_id,
        version=deployment.version,
        environment=deployment.environment,
        status=DeploymentStatus.PENDING,
        endpoint_url=endpoint_url,
        api_key=api_key,
        config=deployment.config,
        deployed_by=user_id,
    )

    db.add(db_deployment)
    await db.commit()
    await db.refresh(db_deployment)

    # Simulate deployment (in real implementation, this would trigger async job)
    db_deployment.status = DeploymentStatus.ACTIVE
    db_deployment.deployed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(db_deployment)

    return db_deployment


@router.get("/", response_model=DeploymentList)
async def list_deployments(
    agent_id: UUID = None,
    environment: DeploymentEnvironment = None,
    status_filter: DeploymentStatus = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """List all deployments with optional filters."""
    query = select(Deployment).order_by(desc(Deployment.created_at))

    if agent_id:
        query = query.where(Deployment.agent_id == agent_id)
    if environment:
        query = query.where(Deployment.environment == environment)
    if status_filter:
        query = query.where(Deployment.status == status_filter)

    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    deployments = result.scalars().all()

    # Get total count
    count_query = select(Deployment)
    if agent_id:
        count_query = count_query.where(Deployment.agent_id == agent_id)
    if environment:
        count_query = count_query.where(Deployment.environment == environment)
    if status_filter:
        count_query = count_query.where(Deployment.status == status_filter)

    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())

    return DeploymentList(deployments=deployments, total=total)


@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific deployment by ID."""
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )

    return deployment


@router.patch("/{deployment_id}", response_model=DeploymentResponse)
async def update_deployment(
    deployment_id: UUID,
    update: DeploymentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a deployment."""
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )

    # Update fields
    if update.status is not None:
        deployment.status = update.status
    if update.endpoint_url is not None:
        deployment.endpoint_url = update.endpoint_url
    if update.error_message is not None:
        deployment.error_message = update.error_message
    if update.config is not None:
        deployment.config = update.config

    await db.commit()
    await db.refresh(deployment)

    return deployment


@router.delete("/{deployment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deployment(
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete/stop a deployment."""
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )

    # Mark as stopped instead of deleting
    deployment.status = DeploymentStatus.STOPPED
    await db.commit()


@router.post("/{deployment_id}/stop", response_model=DeploymentResponse)
async def stop_deployment(
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Stop a running deployment."""
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )

    if deployment.status != DeploymentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deployment is not active",
        )

    deployment.status = DeploymentStatus.STOPPED
    await db.commit()
    await db.refresh(deployment)

    return deployment


@router.post("/{deployment_id}/restart", response_model=DeploymentResponse)
async def restart_deployment(
    deployment_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Restart a stopped deployment."""
    result = await db.execute(select(Deployment).where(Deployment.id == deployment_id))
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        )

    if deployment.status not in [DeploymentStatus.STOPPED, DeploymentStatus.FAILED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deployment cannot be restarted",
        )

    deployment.status = DeploymentStatus.DEPLOYING
    await db.commit()

    # Simulate deployment
    deployment.status = DeploymentStatus.ACTIVE
    deployment.deployed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(deployment)

    return deployment
