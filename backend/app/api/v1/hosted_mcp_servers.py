"""
API endpoints for Hosted MCP Servers.

Manages MCP servers deployed to Azure Container Apps.
"""
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_active_user, get_effective_organization_id
from app.models.user import User
from app.models.hosted_mcp_server import HostedMCPServer, HostedMCPServerStatus, HostedMCPServerSourceType
from app.schemas.hosted_mcp_server import (
    HostedMCPServerCreate,
    HostedMCPServerUpdate,
    HostedMCPServerResponse,
    HostedMCPServerListResponse,
    HostedMCPServerLogs,
    HostedMCPServerDiscoveryResponse,
    ToolExecuteRequest,
    ToolExecuteResponse,
    DiscoveredTool,
    DiscoveredResource,
    DiscoveredPrompt,
)
from app.services.azure_container_apps import (
    azure_container_apps_service,
    ContainerAppConfig,
    ContainerAppStatus,
)
from app.services.azure_acr import azure_acr_service

logger = logging.getLogger(__name__)

router = APIRouter()


def server_to_response(server: HostedMCPServer) -> dict:
    """Convert HostedMCPServer model to response dict."""
    return {
        "id": server.id,
        "organization_id": server.organization_id,
        "creator_id": server.creator_id,
        "name": server.name,
        "description": server.description,
        "source_type": server.source_type,
        "source_config": server.source_config or {},
        "azure_app_name": server.azure_app_name,
        "azure_app_url": server.azure_app_url,
        "azure_resource_id": server.azure_resource_id,
        "environment_variables": server.environment_variables or {},
        "port": server.port,
        "cpu_cores": float(server.cpu_cores) if server.cpu_cores else 0.25,
        "memory_gb": float(server.memory_gb) if server.memory_gb else 0.5,
        "min_replicas": server.min_replicas,
        "max_replicas": server.max_replicas,
        "status": server.status,
        "last_health_check": server.last_health_check,
        "error_message": server.error_message,
        "discovered_tools": server.discovered_tools or [],
        "discovered_resources": server.discovered_resources or [],
        "discovered_prompts": server.discovered_prompts or [],
        "tool_count": len(server.discovered_tools or []),
        "resource_count": len(server.discovered_resources or []),
        "prompt_count": len(server.discovered_prompts or []),
        "created_at": server.created_at,
        "updated_at": server.updated_at,
    }


async def deploy_server_background(
    server_id: UUID,
    db: AsyncSession,
):
    """Background task to deploy a hosted MCP server to Azure."""
    try:
        # Fetch the server
        result = await db.execute(
            select(HostedMCPServer).where(
                HostedMCPServer.id == server_id,
                HostedMCPServer.deleted_at.is_(None),
            )
        )
        server = result.scalar_one_or_none()

        if not server:
            logger.error(f"Server not found for deployment: {server_id}")
            return

        # Update status to deploying
        server.status = HostedMCPServerStatus.DEPLOYING.value
        await db.commit()

        # Determine image based on source type
        image_uri = None
        source_type = server.source_type
        source_config = server.source_config or {}

        if source_type == HostedMCPServerSourceType.DOCKER.value:
            # Use the provided Docker image directly
            image_uri = source_config.get("image")
            if not image_uri:
                raise ValueError("Docker source config missing 'image' field")

        elif source_type == HostedMCPServerSourceType.REGISTRY.value:
            # Build from npm package
            package = source_config.get("package")
            version = source_config.get("version", "latest")
            if not package:
                raise ValueError("Registry source config missing 'package' field")

            build_result = await azure_acr_service.build_from_registry(
                package_name=package,
                version=version,
            )
            if not build_result.success:
                raise ValueError(f"Failed to build image: {build_result.error_message}")
            image_uri = build_result.image_uri

        elif source_type == HostedMCPServerSourceType.GITHUB.value:
            # Build from GitHub repo
            repo = source_config.get("repo")
            branch = source_config.get("branch", "main")
            dockerfile_path = source_config.get("dockerfile_path", "Dockerfile")
            if not repo:
                raise ValueError("GitHub source config missing 'repo' field")

            build_result = await azure_acr_service.build_from_github(
                repo=repo,
                branch=branch,
                dockerfile_path=dockerfile_path,
            )
            if not build_result.success:
                raise ValueError(f"Failed to build image: {build_result.error_message}")
            image_uri = build_result.image_uri

        else:
            raise ValueError(f"Unknown source type: {source_type}")

        # Generate app name
        app_name = azure_container_apps_service.generate_app_name(
            base_name=server.name,
            organization_id=str(server.organization_id),
        )

        # Prepare secrets from environment variables
        secrets = []
        clean_env_vars = {}
        for key, value in (server.environment_variables or {}).items():
            if value.startswith("{{credential:"):
                # TODO: Resolve credential references
                # For now, skip these and log a warning
                logger.warning(f"Credential reference not resolved: {key}")
                continue
            elif "SECRET" in key.upper() or "PASSWORD" in key.upper() or "KEY" in key.upper():
                # Add to secrets
                secret_name = key.lower().replace("_", "-")
                secrets.append({"name": secret_name, "value": value})
                clean_env_vars[key] = f"secretref:{secret_name}"
            else:
                clean_env_vars[key] = value

        # Create container app config
        config = ContainerAppConfig(
            name=app_name,
            image=image_uri,
            port=server.port,
            cpu_cores=float(server.cpu_cores),
            memory_gb=float(server.memory_gb),
            min_replicas=server.min_replicas,
            max_replicas=server.max_replicas,
            environment_variables=clean_env_vars,
            secrets=secrets if secrets else None,
        )

        # Deploy to Azure
        deploy_result = await azure_container_apps_service.deploy_container_app(config)

        if deploy_result.provisioning_state == "Succeeded":
            server.status = HostedMCPServerStatus.RUNNING.value
            server.azure_app_name = app_name
            server.azure_app_url = f"https://{deploy_result.fqdn}" if deploy_result.fqdn else None
            server.azure_resource_id = deploy_result.resource_id
            server.error_message = None
        else:
            server.status = HostedMCPServerStatus.FAILED.value
            server.azure_app_name = app_name
            server.error_message = deploy_result.error_message or "Deployment failed"

        server.updated_at = datetime.utcnow()
        await db.commit()

        logger.info(f"Server deployment completed: {server_id}, status: {server.status}")

    except Exception as e:
        logger.error(f"Error deploying server {server_id}: {e}")
        try:
            result = await db.execute(
                select(HostedMCPServer).where(HostedMCPServer.id == server_id)
            )
            server = result.scalar_one_or_none()
            if server:
                server.status = HostedMCPServerStatus.FAILED.value
                server.error_message = str(e)
                server.updated_at = datetime.utcnow()
                await db.commit()
        except Exception as commit_error:
            logger.error(f"Error updating server status: {commit_error}")


@router.get("", response_model=HostedMCPServerListResponse)
async def list_hosted_mcp_servers(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
):
    """List all hosted MCP servers for the organization."""
    conditions = [
        HostedMCPServer.organization_id == effective_org_id,
        HostedMCPServer.deleted_at.is_(None),
    ]

    if status_filter:
        conditions.append(HostedMCPServer.status == status_filter)

    # Get total count
    count_query = select(func.count(HostedMCPServer.id)).where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get servers
    query = (
        select(HostedMCPServer)
        .where(*conditions)
        .order_by(HostedMCPServer.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    servers = result.scalars().all()

    return {
        "servers": [server_to_response(s) for s in servers],
        "total": total,
    }


@router.post("", response_model=HostedMCPServerResponse, status_code=status.HTTP_201_CREATED)
async def create_hosted_mcp_server(
    server_data: HostedMCPServerCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
):
    """
    Create and deploy a new hosted MCP server.

    The server will be deployed to Azure Container Apps asynchronously.
    Check the status field to monitor deployment progress.
    """
    # Check for duplicate name
    existing = await db.execute(
        select(HostedMCPServer).where(
            HostedMCPServer.organization_id == effective_org_id,
            HostedMCPServer.name == server_data.name,
            HostedMCPServer.deleted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A server with name '{server_data.name}' already exists",
        )

    # Create server record
    server = HostedMCPServer(
        organization_id=effective_org_id,
        creator_id=current_user.id,
        name=server_data.name,
        description=server_data.description,
        source_type=server_data.source_type.value,
        source_config=server_data.source_config,
        environment_variables=server_data.environment_variables or {},
        port=server_data.port,
        cpu_cores=server_data.cpu_cores,
        memory_gb=server_data.memory_gb,
        min_replicas=server_data.min_replicas,
        max_replicas=server_data.max_replicas,
        status=HostedMCPServerStatus.PENDING.value,
    )

    db.add(server)
    await db.commit()
    await db.refresh(server)

    # Start deployment in background
    background_tasks.add_task(deploy_server_background, server.id, db)

    return server_to_response(server)


@router.get("/{server_id}", response_model=HostedMCPServerResponse)
async def get_hosted_mcp_server(
    server_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
):
    """Get details of a hosted MCP server."""
    result = await db.execute(
        select(HostedMCPServer).where(
            HostedMCPServer.id == server_id,
            HostedMCPServer.organization_id == effective_org_id,
            HostedMCPServer.deleted_at.is_(None),
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hosted MCP server not found",
        )

    return server_to_response(server)


@router.patch("/{server_id}", response_model=HostedMCPServerResponse)
async def update_hosted_mcp_server(
    server_id: UUID,
    server_data: HostedMCPServerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
):
    """
    Update a hosted MCP server configuration.

    Note: Changes to cpu_cores, memory_gb, or replicas will require a redeploy.
    """
    result = await db.execute(
        select(HostedMCPServer).where(
            HostedMCPServer.id == server_id,
            HostedMCPServer.organization_id == effective_org_id,
            HostedMCPServer.deleted_at.is_(None),
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hosted MCP server not found",
        )

    # Update fields
    update_data = server_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(server, field, value)

    server.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(server)

    return server_to_response(server)


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hosted_mcp_server(
    server_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
):
    """
    Delete a hosted MCP server.

    This will stop and remove the Azure Container App.
    """
    result = await db.execute(
        select(HostedMCPServer).where(
            HostedMCPServer.id == server_id,
            HostedMCPServer.organization_id == effective_org_id,
            HostedMCPServer.deleted_at.is_(None),
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hosted MCP server not found",
        )

    # Delete from Azure if deployed
    if server.azure_app_name:
        try:
            await azure_container_apps_service.delete_container_app(server.azure_app_name)
        except Exception as e:
            logger.error(f"Error deleting Azure container app: {e}")
            # Continue with soft delete anyway

    # Soft delete
    server.deleted_at = datetime.utcnow()
    server.status = HostedMCPServerStatus.DELETED.value
    await db.commit()


@router.post("/{server_id}/start", response_model=HostedMCPServerResponse)
async def start_hosted_mcp_server(
    server_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
):
    """Start a stopped hosted MCP server."""
    result = await db.execute(
        select(HostedMCPServer).where(
            HostedMCPServer.id == server_id,
            HostedMCPServer.organization_id == effective_org_id,
            HostedMCPServer.deleted_at.is_(None),
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hosted MCP server not found",
        )

    if not server.azure_app_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server has not been deployed yet",
        )

    # Start the container app
    start_result = await azure_container_apps_service.start_container_app(
        server.azure_app_name,
        min_replicas=server.min_replicas if server.min_replicas > 0 else 1,
    )

    if start_result.provisioning_state == "Succeeded":
        server.status = HostedMCPServerStatus.RUNNING.value
        server.error_message = None
    else:
        server.status = HostedMCPServerStatus.FAILED.value
        server.error_message = start_result.error_message

    server.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(server)

    return server_to_response(server)


@router.post("/{server_id}/stop", response_model=HostedMCPServerResponse)
async def stop_hosted_mcp_server(
    server_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
):
    """Stop a running hosted MCP server (scale to zero)."""
    result = await db.execute(
        select(HostedMCPServer).where(
            HostedMCPServer.id == server_id,
            HostedMCPServer.organization_id == effective_org_id,
            HostedMCPServer.deleted_at.is_(None),
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hosted MCP server not found",
        )

    if not server.azure_app_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server has not been deployed yet",
        )

    # Stop the container app
    stop_result = await azure_container_apps_service.stop_container_app(server.azure_app_name)

    if stop_result.provisioning_state == "Succeeded":
        server.status = HostedMCPServerStatus.STOPPED.value
        server.error_message = None
    else:
        server.error_message = stop_result.error_message

    server.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(server)

    return server_to_response(server)


@router.post("/{server_id}/redeploy", response_model=HostedMCPServerResponse)
async def redeploy_hosted_mcp_server(
    server_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
):
    """
    Force redeploy a hosted MCP server.

    This will rebuild and redeploy the server with the latest image.
    """
    result = await db.execute(
        select(HostedMCPServer).where(
            HostedMCPServer.id == server_id,
            HostedMCPServer.organization_id == effective_org_id,
            HostedMCPServer.deleted_at.is_(None),
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hosted MCP server not found",
        )

    # Set status to deploying
    server.status = HostedMCPServerStatus.DEPLOYING.value
    server.updated_at = datetime.utcnow()
    await db.commit()

    # Start deployment in background
    background_tasks.add_task(deploy_server_background, server.id, db)

    await db.refresh(server)
    return server_to_response(server)


@router.get("/{server_id}/logs", response_model=HostedMCPServerLogs)
async def get_hosted_mcp_server_logs(
    server_id: UUID,
    lines: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
):
    """Get container logs for a hosted MCP server."""
    result = await db.execute(
        select(HostedMCPServer).where(
            HostedMCPServer.id == server_id,
            HostedMCPServer.organization_id == effective_org_id,
            HostedMCPServer.deleted_at.is_(None),
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hosted MCP server not found",
        )

    if not server.azure_app_name:
        return {
            "logs": "Server has not been deployed yet",
            "timestamp": datetime.utcnow(),
        }

    logs = await azure_container_apps_service.get_container_logs(
        server.azure_app_name,
        lines=lines,
    )

    return {
        "logs": logs,
        "timestamp": datetime.utcnow(),
    }


@router.post("/{server_id}/discover", response_model=HostedMCPServerDiscoveryResponse)
async def discover_hosted_mcp_server_capabilities(
    server_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
):
    """
    Discover MCP capabilities from a running server.

    This connects to the MCP server and retrieves available tools, resources, and prompts.
    """
    result = await db.execute(
        select(HostedMCPServer).where(
            HostedMCPServer.id == server_id,
            HostedMCPServer.organization_id == effective_org_id,
            HostedMCPServer.deleted_at.is_(None),
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hosted MCP server not found",
        )

    if server.status != HostedMCPServerStatus.RUNNING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server must be running to discover capabilities",
        )

    if not server.azure_app_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server URL not available",
        )

    # TODO: Connect to MCP server and discover capabilities
    # For now, return placeholder data
    discovered_tools = []
    discovered_resources = []
    discovered_prompts = []

    try:
        # Import MCP service
        from app.services.mcp_service import MCPService, MCPConfig

        # Create MCP client config
        mcp_config = MCPConfig(
            server_url=server.azure_app_url,
            transport_type="sse",
        )

        # Connect and discover
        mcp_service = MCPService(mcp_config)

        # Get tools
        tools = await mcp_service.list_tools()
        for tool in tools:
            discovered_tools.append({
                "name": tool.get("name", ""),
                "description": tool.get("description"),
                "input_schema": tool.get("input_schema") or tool.get("inputSchema"),
            })

        # Get resources (if supported)
        try:
            resources = await mcp_service.list_resources()
            for resource in resources:
                discovered_resources.append({
                    "uri": resource.get("uri", ""),
                    "name": resource.get("name"),
                    "description": resource.get("description"),
                    "mime_type": resource.get("mimeType") or resource.get("mime_type"),
                })
        except Exception:
            pass  # Resources may not be supported

        # Get prompts (if supported)
        try:
            prompts = await mcp_service.list_prompts()
            for prompt in prompts:
                discovered_prompts.append({
                    "name": prompt.get("name", ""),
                    "description": prompt.get("description"),
                    "arguments": prompt.get("arguments"),
                })
        except Exception:
            pass  # Prompts may not be supported

    except Exception as e:
        logger.error(f"Error discovering MCP capabilities: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to connect to MCP server: {str(e)}",
        )

    # Update server with discovered capabilities
    server.discovered_tools = discovered_tools
    server.discovered_resources = discovered_resources
    server.discovered_prompts = discovered_prompts
    server.last_health_check = datetime.utcnow()
    server.updated_at = datetime.utcnow()
    await db.commit()

    return {
        "tools": [DiscoveredTool(**t) for t in discovered_tools],
        "resources": [DiscoveredResource(**r) for r in discovered_resources],
        "prompts": [DiscoveredPrompt(**p) for p in discovered_prompts],
        "discovered_at": datetime.utcnow(),
    }


@router.post("/{server_id}/tools/{tool_name}/execute", response_model=ToolExecuteResponse)
async def execute_hosted_mcp_server_tool(
    server_id: UUID,
    tool_name: str,
    request: ToolExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    effective_org_id: UUID = Depends(get_effective_organization_id),
):
    """Execute a tool on a hosted MCP server."""
    result = await db.execute(
        select(HostedMCPServer).where(
            HostedMCPServer.id == server_id,
            HostedMCPServer.organization_id == effective_org_id,
            HostedMCPServer.deleted_at.is_(None),
        )
    )
    server = result.scalar_one_or_none()

    if not server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hosted MCP server not found",
        )

    if server.status != HostedMCPServerStatus.RUNNING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server must be running to execute tools",
        )

    if not server.azure_app_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server URL not available",
        )

    import time
    start_time = time.time()

    try:
        # Import MCP service
        from app.services.mcp_service import MCPService, MCPConfig

        # Create MCP client config
        mcp_config = MCPConfig(
            server_url=server.azure_app_url,
            transport_type="sse",
        )

        # Connect and execute tool
        mcp_service = MCPService(mcp_config)
        tool_result = await mcp_service.call_tool(tool_name, request.arguments)

        execution_time_ms = int((time.time() - start_time) * 1000)

        return {
            "success": True,
            "result": tool_result,
            "execution_time_ms": execution_time_ms,
        }

    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Error executing tool {tool_name}: {e}")

        return {
            "success": False,
            "error": str(e),
            "execution_time_ms": execution_time_ms,
        }
