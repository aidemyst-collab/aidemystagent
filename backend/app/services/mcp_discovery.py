"""
MCP Discovery Service - Discovers tools, resources, and prompts from MCP servers
"""
import logging
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from app.services.mcp_service import mcp_service

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryResult:
    """Result of MCP server discovery."""
    success: bool
    tools: List[Dict[str, Any]]
    resources: List[Dict[str, Any]]
    prompts: List[Dict[str, Any]]
    error: Optional[str] = None
    response_time_ms: Optional[int] = None


@dataclass
class HealthCheckResult:
    """Result of MCP server health check."""
    success: bool
    response_time_ms: Optional[int] = None
    server_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class MCPDiscoveryService:
    """Service for discovering capabilities from MCP servers."""

    async def test_connection(
        self,
        server_url: str,
        auth_token: Optional[str] = None
    ) -> HealthCheckResult:
        """
        Test connection to an MCP server.

        Args:
            server_url: URL of the MCP server
            auth_token: Optional authentication token

        Returns:
            HealthCheckResult with connection status
        """
        start_time = time.time()

        try:
            logger.info(f"Testing connection to MCP server: {server_url}")

            # Try to list tools as a health check
            result = await mcp_service.list_tools(
                server_url=server_url,
                auth_token=auth_token
            )

            elapsed_ms = int((time.time() - start_time) * 1000)

            if result.success:
                return HealthCheckResult(
                    success=True,
                    response_time_ms=elapsed_ms,
                    server_info={
                        "tools_count": len(result.result.get("tools", [])) if isinstance(result.result, dict) else 0,
                        "url": server_url
                    }
                )
            else:
                return HealthCheckResult(
                    success=False,
                    response_time_ms=elapsed_ms,
                    error=result.error or "Failed to connect to MCP server"
                )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.exception(f"Error testing MCP server connection: {str(e)}")
            return HealthCheckResult(
                success=False,
                response_time_ms=elapsed_ms,
                error=str(e)
            )

    async def discover_capabilities(
        self,
        server_url: str,
        auth_token: Optional[str] = None
    ) -> DiscoveryResult:
        """
        Discover all capabilities (tools, resources, prompts) from an MCP server.

        Args:
            server_url: URL of the MCP server
            auth_token: Optional authentication token

        Returns:
            DiscoveryResult with discovered capabilities
        """
        start_time = time.time()
        tools = []
        resources = []
        prompts = []
        errors = []

        try:
            logger.info(f"Discovering capabilities from MCP server: {server_url}")

            # Discover tools
            tools_result = await mcp_service.list_tools(
                server_url=server_url,
                auth_token=auth_token
            )

            if tools_result.success and isinstance(tools_result.result, dict):
                raw_tools = tools_result.result.get("tools", [])
                for tool in raw_tools:
                    tools.append({
                        "name": tool.get("name", "unknown"),
                        "description": tool.get("description"),
                        "input_schema": tool.get("inputSchema") or tool.get("input_schema")
                    })
                logger.info(f"Discovered {len(tools)} tools")
            else:
                errors.append(f"Failed to discover tools: {tools_result.error}")

            # Discover resources
            resources_result = await mcp_service.list_resources(
                server_url=server_url,
                auth_token=auth_token
            )

            if resources_result.success and isinstance(resources_result.result, dict):
                raw_resources = resources_result.result.get("resources", [])
                for resource in raw_resources:
                    resources.append({
                        "uri": resource.get("uri", ""),
                        "name": resource.get("name"),
                        "description": resource.get("description"),
                        "mime_type": resource.get("mimeType") or resource.get("mime_type")
                    })
                logger.info(f"Discovered {len(resources)} resources")
            else:
                # Resources may not be supported by all servers
                logger.debug(f"No resources discovered: {resources_result.error}")

            # Discover prompts
            prompts_result = await mcp_service.list_prompts(
                server_url=server_url,
                auth_token=auth_token
            )

            if prompts_result.success and isinstance(prompts_result.result, dict):
                raw_prompts = prompts_result.result.get("prompts", [])
                for prompt in raw_prompts:
                    prompts.append({
                        "name": prompt.get("name", "unknown"),
                        "description": prompt.get("description"),
                        "arguments": prompt.get("arguments", [])
                    })
                logger.info(f"Discovered {len(prompts)} prompts")
            else:
                # Prompts may not be supported by all servers
                logger.debug(f"No prompts discovered: {prompts_result.error}")

            elapsed_ms = int((time.time() - start_time) * 1000)

            return DiscoveryResult(
                success=True,
                tools=tools,
                resources=resources,
                prompts=prompts,
                response_time_ms=elapsed_ms
            )

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.exception(f"Error discovering MCP server capabilities: {str(e)}")
            return DiscoveryResult(
                success=False,
                tools=tools,
                resources=resources,
                prompts=prompts,
                error=str(e),
                response_time_ms=elapsed_ms
            )


# Singleton instance
mcp_discovery_service = MCPDiscoveryService()
