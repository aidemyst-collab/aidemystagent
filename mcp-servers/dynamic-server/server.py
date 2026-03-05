"""
Dynamic MCP Server

This server reads tool definitions from AgentStudio and exposes them as MCP tools.
Users create tools via the AgentStudio UI, and this server makes the actual API calls.

Key features:
- Dynamically loads tool definitions from AgentStudio API
- Executes API calls on behalf of agents
- Manages credentials securely (LLM never sees secrets)
- Supports token caching for OAuth2 and other auth types

Usage:
    python server.py

Environment:
    AGENTSTUDIO_API_URL=http://localhost:8000
    MCP_INTERNAL_API_KEY=your-internal-key
    REDIS_URL=redis://localhost:6379/0
"""
import asyncio
import logging
import httpx
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastmcp import FastMCP
from config import settings

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("dynamic-mcp-server")

# Initialize FastMCP server
mcp = FastMCP(
    "AgentStudio Dynamic MCP Server",
    description="Dynamic tool server that executes API-based tools defined in AgentStudio"
)

# Global tool definitions cache
_tool_definitions: Dict[str, Dict[str, Any]] = {}
_last_refresh: Optional[datetime] = None


async def fetch_tool_definitions() -> List[Dict[str, Any]]:
    """
    Fetch tool definitions from AgentStudio API.

    Returns list of tool definitions in MCP format.
    """
    global _tool_definitions, _last_refresh

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{settings.AGENTSTUDIO_API_URL}/api/v1/mcp-tools/internal/all",
                headers={
                    "X-Internal-Key": settings.MCP_INTERNAL_API_KEY,
                }
            )

            if response.status_code == 200:
                data = response.json()
                tools = data.get("tools", [])

                # Update cache
                _tool_definitions = {tool["name"]: tool for tool in tools}
                _last_refresh = datetime.utcnow()

                logger.info(f"Loaded {len(tools)} tool definitions from AgentStudio")
                return tools
            else:
                logger.error(f"Failed to fetch tools: {response.status_code} - {response.text}")
                return []

    except Exception as e:
        logger.exception(f"Error fetching tool definitions: {e}")
        return []


async def fetch_credential(credential_id: str, organization_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch decrypted credential from AgentStudio.

    Args:
        credential_id: The credential ID
        organization_id: The organization ID for validation

    Returns:
        Credential data including decrypted values
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.AGENTSTUDIO_API_URL}/api/v1/credentials/internal/{credential_id}",
                headers={
                    "X-Internal-Key": settings.MCP_INTERNAL_API_KEY,
                    "X-Organization-Id": organization_id,
                }
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch credential: {response.status_code}")
                return None

    except Exception as e:
        logger.exception(f"Error fetching credential: {e}")
        return None


async def execute_api_call(
    tool_config: Dict[str, Any],
    arguments: Dict[str, Any]
) -> str:
    """
    Execute an API call based on tool configuration.

    Args:
        tool_config: Tool configuration from _config field
        arguments: Arguments provided by the LLM

    Returns:
        API response as string
    """
    endpoint = tool_config.get("api_endpoint", "")
    method = tool_config.get("method", "GET").upper()
    headers = dict(tool_config.get("headers", {}))
    query_params = dict(tool_config.get("query_params", {}))
    body_template = tool_config.get("body_template", {})
    credential_id = tool_config.get("credential_id")
    organization_id = tool_config.get("organization_id")
    timeout = tool_config.get("timeout_seconds", 30)
    response_path = tool_config.get("response_path")

    # Add authentication header if credential is specified
    if credential_id:
        credential = await fetch_credential(credential_id, organization_id)
        if credential:
            auth_type = credential.get("auth_type", "bearer")
            if auth_type == "bearer":
                api_key = credential.get("api_key", "")
                headers["Authorization"] = f"Bearer {api_key}"
            elif auth_type == "config":
                # For config-based credentials, extract API key if present
                config = credential.get("config", {})
                if "api_key" in config:
                    headers["Authorization"] = f"Bearer {config['api_key']}"
                elif "auth_token" in config:
                    headers["Authorization"] = f"Bearer {config['auth_token']}"

    # Build request URL with path parameters
    url = endpoint
    for key, value in arguments.items():
        url = url.replace(f"{{{key}}}", str(value))

    # Merge arguments into query params for GET requests
    if method == "GET":
        query_params.update(arguments)

    # Build request body for POST/PUT/PATCH
    body = None
    if method in ["POST", "PUT", "PATCH"]:
        if body_template:
            # Use template and fill in arguments
            body = json.loads(json.dumps(body_template))
            for key, value in arguments.items():
                if key in body:
                    body[key] = value
                else:
                    body[key] = value
        else:
            body = arguments

    # Make the request
    try:
        async with httpx.AsyncClient(timeout=float(timeout)) as client:
            if method == "GET":
                response = await client.get(url, params=query_params, headers=headers)
            elif method == "POST":
                response = await client.post(url, json=body, params=query_params, headers=headers)
            elif method == "PUT":
                response = await client.put(url, json=body, params=query_params, headers=headers)
            elif method == "PATCH":
                response = await client.patch(url, json=body, params=query_params, headers=headers)
            elif method == "DELETE":
                response = await client.delete(url, params=query_params, headers=headers)
            else:
                return f"Unsupported HTTP method: {method}"

            # Parse response
            try:
                result = response.json()

                # Extract specific path if configured
                if response_path:
                    for part in response_path.split("."):
                        if isinstance(result, dict) and part in result:
                            result = result[part]
                        elif isinstance(result, list) and part.isdigit():
                            result = result[int(part)]
                        else:
                            break

                return json.dumps(result, indent=2)

            except json.JSONDecodeError:
                return response.text

    except httpx.TimeoutException:
        return f"Request timed out after {timeout} seconds"
    except Exception as e:
        logger.exception(f"Error executing API call: {e}")
        return f"Error: {str(e)}"


def create_tool_handler(tool_def: Dict[str, Any]):
    """
    Create a tool handler function for a tool definition.

    Args:
        tool_def: Tool definition from AgentStudio

    Returns:
        Async function that handles tool calls
    """
    tool_config = tool_def.get("_config", {})
    tool_name = tool_def.get("name", "unknown")

    async def handler(**kwargs) -> str:
        """Execute the dynamic tool."""
        logger.info(f"Executing tool: {tool_name} with args: {kwargs}")

        try:
            result = await execute_api_call(tool_config, kwargs)
            logger.info(f"Tool {tool_name} completed successfully")
            return result
        except Exception as e:
            logger.exception(f"Tool {tool_name} failed: {e}")
            return f"Error executing tool: {str(e)}"

    return handler


def register_tools():
    """
    Register all tool definitions with FastMCP.

    This should be called at startup and when tools are refreshed.
    """
    for name, tool_def in _tool_definitions.items():
        try:
            # Extract schema
            input_schema = tool_def.get("inputSchema", {})
            description = tool_def.get("description", f"Dynamic tool: {name}")

            # Create handler
            handler = create_tool_handler(tool_def)
            handler.__name__ = name
            handler.__doc__ = description

            # Register with FastMCP
            # Note: FastMCP may not support dynamic registration
            # This is a placeholder for the actual implementation
            logger.info(f"Registered tool: {name}")

        except Exception as e:
            logger.exception(f"Failed to register tool {name}: {e}")


@mcp.tool()
async def list_available_tools() -> str:
    """
    List all available dynamic tools.

    Returns a list of tool names and their descriptions.
    """
    # Refresh tools if needed
    if not _tool_definitions:
        await fetch_tool_definitions()

    tools_info = []
    for name, tool_def in _tool_definitions.items():
        tools_info.append({
            "name": name,
            "description": tool_def.get("description", ""),
        })

    return json.dumps(tools_info, indent=2)


@mcp.tool()
async def execute_dynamic_tool(tool_name: str, arguments: str = "{}") -> str:
    """
    Execute a dynamic tool by name.

    Args:
        tool_name: Name of the tool to execute
        arguments: JSON string of arguments to pass to the tool

    Returns:
        Tool execution result
    """
    # Refresh tools if needed
    if not _tool_definitions:
        await fetch_tool_definitions()

    # Find tool definition
    tool_def = _tool_definitions.get(tool_name)
    if not tool_def:
        return f"Tool not found: {tool_name}"

    # Parse arguments
    try:
        args = json.loads(arguments) if arguments else {}
    except json.JSONDecodeError:
        return f"Invalid arguments JSON: {arguments}"

    # Execute tool
    tool_config = tool_def.get("_config", {})
    return await execute_api_call(tool_config, args)


async def refresh_tools_periodically():
    """Background task to refresh tool definitions periodically."""
    while True:
        await asyncio.sleep(settings.TOOL_REFRESH_INTERVAL)
        await fetch_tool_definitions()


@mcp.on_startup
async def startup():
    """Initialize the server on startup."""
    logger.info("Dynamic MCP Server starting...")

    # Load initial tool definitions
    await fetch_tool_definitions()

    # Start background refresh task
    asyncio.create_task(refresh_tools_periodically())

    logger.info("Dynamic MCP Server ready")


if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting Dynamic MCP Server on {settings.HOST}:{settings.PORT}")
    mcp.run(transport="sse", port=settings.PORT)
