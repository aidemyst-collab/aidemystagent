"""
MCP Service - FastMCP Client Implementation

Connects to external MCP servers and executes operations.
Supports resources, tools, and prompts.

Usage:
    from app.services.mcp_service import mcp_service

    result = await mcp_service.execute(
        mcp_type="tool",
        resource_uri="query_database",
        server_url="http://mcp-server:3000/sse",
        input_data={"query": "SELECT * FROM users"}
    )
"""

import httpx
import logging
import time
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager


# Try to import FastMCP client
try:
    from fastmcp import Client
    from fastmcp.client.transports import SSETransport, StreamableHttpTransport
    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False
    logging.warning("FastMCP not installed. Install with: pip install 'fastmcp<3'")


logger = logging.getLogger(__name__)


class MCPType(str, Enum):
    """MCP operation types."""
    RESOURCE = "resource"
    TOOL = "tool"
    PROMPT = "prompt"


@dataclass
class MCPResult:
    """Result of an MCP operation."""
    success: bool
    result: Any
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None


@dataclass
class MCPConfig:
    """Configuration for MCP service."""
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0
    http_fallback_endpoint_pattern: str = "/tools/{tool_name}"


class MCPService:
    """
    FastMCP Client Service for connecting to MCP servers.

    Supports:
    - Reading resources (files, data)
    - Calling tools (functions, actions)
    - Getting prompts (templates)
    - Configurable timeouts and retry logic
    - HTTP fallback for simple MCP servers

    Example:
        mcp = MCPService()

        # Call a tool
        result = await mcp.call_tool(
            server_url="http://localhost:3000/sse",
            tool_name="search",
            arguments={"query": "python"}
        )

        # With custom config
        mcp = MCPService(config=MCPConfig(timeout=60, max_retries=5))
    """

    def __init__(self, config: MCPConfig = None):
        self.config = config or MCPConfig()

    # =========================================================================
    # Retry Logic
    # =========================================================================

    async def _with_retry(self, operation, *args, **kwargs) -> Any:
        """
        Execute an operation with retry logic for transient failures.

        Args:
            operation: Async function to execute
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation

        Returns:
            Result of the operation

        Raises:
            Exception: If all retries are exhausted
        """
        last_exception = None
        delay = self.config.retry_delay

        for attempt in range(self.config.max_retries):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                error_str = str(e).lower()

                # Check if error is retryable (transient)
                retryable_errors = [
                    "connection",
                    "timeout",
                    "temporarily",
                    "unavailable",
                    "503",
                    "502",
                    "504",
                    "reset",
                    "broken pipe",
                ]

                is_retryable = any(err in error_str for err in retryable_errors)

                if not is_retryable or attempt == self.config.max_retries - 1:
                    raise

                logger.warning(
                    f"Retry {attempt + 1}/{self.config.max_retries} after error: {e}. "
                    f"Waiting {delay}s..."
                )
                await asyncio.sleep(delay)
                delay *= self.config.retry_backoff

        raise last_exception

    # =========================================================================
    # Connection Management
    # =========================================================================

    @asynccontextmanager
    async def _get_client(
        self,
        server_url: str,
        auth_token: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None
    ):
        """
        Create a FastMCP client connection with timeout.

        Args:
            server_url: MCP server URL (SSE or HTTP endpoint)
            auth_token: Optional Bearer token for authentication
            headers: Optional additional headers

        Yields:
            Connected FastMCP Client
        """
        if not FASTMCP_AVAILABLE:
            raise RuntimeError("FastMCP not installed. Run: pip install 'fastmcp<3'")

        # Build headers with auth
        request_headers = dict(headers) if headers else {}
        if auth_token:
            request_headers["Authorization"] = f"Bearer {auth_token}"

        # Determine transport based on URL
        if server_url.startswith("http"):
            if "/sse" in server_url:
                # SSE Transport (backward compatibility)
                transport = SSETransport(
                    url=server_url,
                    headers=request_headers,
                    timeout=self.config.timeout
                )
            else:
                # Streamable HTTP Transport (recommended)
                transport = StreamableHttpTransport(
                    url=server_url,
                    headers=request_headers,
                    timeout=self.config.timeout
                )
        else:
            raise ValueError(f"Unsupported URL scheme: {server_url}. Use http:// or https://")

        # Create client with timeout
        client = Client(transport)

        try:
            async with asyncio.timeout(self.config.timeout):
                async with client:
                    yield client
        except asyncio.TimeoutError:
            raise TimeoutError(f"Connection to MCP server timed out after {self.config.timeout}s")

    # =========================================================================
    # Resource Operations
    # =========================================================================

    async def list_resources(self, server_url: str, auth_token: str = None) -> MCPResult:
        """
        List available resources from an MCP server.

        Args:
            server_url: MCP server endpoint
            auth_token: Optional authentication token

        Returns:
            MCPResult with list of resources
        """
        start_time = time.time()

        async def _operation():
            async with self._get_client(server_url, auth_token) as client:
                resources = await client.list_resources()
                return [
                    {
                        "uri": str(r.uri),
                        "name": r.name,
                        "description": getattr(r, 'description', None),
                        "mimeType": getattr(r, 'mimeType', None)
                    }
                    for r in resources
                ]

        try:
            resources = await self._with_retry(_operation)
            return MCPResult(
                success=True,
                result={"resources": resources},
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        except Exception as e:
            logger.error(f"Failed to list resources: {e}")
            return MCPResult(
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

    async def read_resource(
        self,
        server_url: str,
        resource_uri: str,
        auth_token: str = None
    ) -> MCPResult:
        """
        Read a resource from an MCP server.

        Args:
            server_url: MCP server endpoint
            resource_uri: URI of the resource to read
            auth_token: Optional authentication token

        Returns:
            MCPResult with resource content
        """
        start_time = time.time()

        async def _operation():
            async with self._get_client(server_url, auth_token) as client:
                content = await client.read_resource(resource_uri)

                # Handle different response formats
                if isinstance(content, list):
                    return [
                        {
                            "uri": resource_uri,
                            "text": getattr(c, 'text', str(c)),
                            "mimeType": getattr(c, 'mimeType', None)
                        }
                        for c in content
                    ]
                else:
                    return [{
                        "uri": resource_uri,
                        "text": getattr(content, 'text', str(content)),
                        "mimeType": getattr(content, 'mimeType', None)
                    }]

        try:
            contents = await self._with_retry(_operation)
            return MCPResult(
                success=True,
                result={"contents": contents},
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        except Exception as e:
            logger.error(f"Failed to read resource {resource_uri}: {e}")
            return MCPResult(
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

    # =========================================================================
    # Tool Operations
    # =========================================================================

    async def list_tools(self, server_url: str, auth_token: str = None) -> MCPResult:
        """
        List available tools from an MCP server.

        Args:
            server_url: MCP server endpoint
            auth_token: Optional authentication token

        Returns:
            MCPResult with list of tools including their schemas
        """
        start_time = time.time()

        async def _operation():
            async with self._get_client(server_url, auth_token) as client:
                tools = await client.list_tools()
                return [
                    {
                        "name": t.name,
                        "description": getattr(t, 'description', None),
                        "inputSchema": getattr(t, 'inputSchema', {})
                    }
                    for t in tools
                ]

        try:
            tools = await self._with_retry(_operation)
            return MCPResult(
                success=True,
                result={"tools": tools},
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return MCPResult(
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

    async def call_tool(
        self,
        server_url: str,
        tool_name: str,
        arguments: Dict[str, Any] = None,
        auth_token: str = None
    ) -> MCPResult:
        """
        Call a tool on an MCP server.

        Args:
            server_url: MCP server endpoint
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            auth_token: Optional authentication token

        Returns:
            MCPResult with tool execution result
        """
        start_time = time.time()

        async def _operation():
            async with self._get_client(server_url, auth_token) as client:
                result = await client.call_tool(tool_name, arguments or {})

                # Parse result - FastMCP returns result with .data attribute
                if hasattr(result, 'data'):
                    return [{"type": "text", "text": str(result.data)}]
                elif hasattr(result, 'content'):
                    return [
                        {
                            "type": getattr(c, 'type', 'text'),
                            "text": getattr(c, 'text', str(c))
                        }
                        for c in result.content
                    ]
                else:
                    return [{"type": "text", "text": str(result)}]

        try:
            content = await self._with_retry(_operation)
            return MCPResult(
                success=True,
                result={"content": content},
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {e}")
            return MCPResult(
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

    # =========================================================================
    # Prompt Operations
    # =========================================================================

    async def list_prompts(self, server_url: str, auth_token: str = None) -> MCPResult:
        """
        List available prompts from an MCP server.

        Args:
            server_url: MCP server endpoint
            auth_token: Optional authentication token

        Returns:
            MCPResult with list of prompts
        """
        start_time = time.time()

        async def _operation():
            async with self._get_client(server_url, auth_token) as client:
                prompts = await client.list_prompts()
                return [
                    {
                        "name": p.name,
                        "description": getattr(p, 'description', None),
                        "arguments": getattr(p, 'arguments', [])
                    }
                    for p in prompts
                ]

        try:
            prompts = await self._with_retry(_operation)
            return MCPResult(
                success=True,
                result={"prompts": prompts},
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        except Exception as e:
            logger.error(f"Failed to list prompts: {e}")
            return MCPResult(
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

    async def get_prompt(
        self,
        server_url: str,
        prompt_name: str,
        arguments: Dict[str, Any] = None,
        auth_token: str = None
    ) -> MCPResult:
        """
        Get a prompt from an MCP server.

        Args:
            server_url: MCP server endpoint
            prompt_name: Name of the prompt
            arguments: Arguments to fill in the template
            auth_token: Optional authentication token

        Returns:
            MCPResult with prompt messages
        """
        start_time = time.time()

        async def _operation():
            async with self._get_client(server_url, auth_token) as client:
                result = await client.get_prompt(prompt_name, arguments or {})
                return [
                    {
                        "role": m.role,
                        "content": str(m.content)
                    }
                    for m in result.messages
                ]

        try:
            messages = await self._with_retry(_operation)
            return MCPResult(
                success=True,
                result={"messages": messages},
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        except Exception as e:
            logger.error(f"Failed to get prompt {prompt_name}: {e}")
            return MCPResult(
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

    # =========================================================================
    # HTTP Fallback (for servers without FastMCP client support)
    # =========================================================================

    async def _http_call_tool(
        self,
        server_url: str,
        tool_name: str,
        arguments: Dict[str, Any] = None,
        auth_token: str = None,
        endpoint_pattern: str = None
    ) -> MCPResult:
        """
        Fallback HTTP-based tool call for simple MCP servers.

        Args:
            server_url: Base server URL
            tool_name: Name of the tool to call
            arguments: Tool arguments
            auth_token: Optional Bearer token
            endpoint_pattern: Custom endpoint pattern (default: /tools/{tool_name})
                              Use {tool_name} as placeholder

        Returns:
            MCPResult with tool execution result
        """
        start_time = time.time()

        # Use custom pattern or default from config
        pattern = endpoint_pattern or self.config.http_fallback_endpoint_pattern
        endpoint_path = pattern.format(tool_name=tool_name)

        async def _operation():
            headers = {"Content-Type": "application/json"}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"

            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                endpoint = f"{server_url.rstrip('/')}{endpoint_path}"

                response = await client.post(
                    endpoint,
                    json={"arguments": arguments or {}},
                    headers=headers
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    raise Exception(f"HTTP {response.status_code}: {response.text}")

        try:
            result = await self._with_retry(_operation)
            return MCPResult(
                success=True,
                result=result,
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
        except Exception as e:
            return MCPResult(
                success=False,
                result=None,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )

    # =========================================================================
    # Main Entry Point
    # =========================================================================

    async def execute(
        self,
        mcp_type: str,
        resource_uri: str,
        server_url: str,
        input_data: Dict[str, Any] = None,
        auth_token: str = None,
        http_fallback_pattern: str = None
    ) -> MCPResult:
        """
        Main entry point for MCP operations.

        Routes to appropriate method based on mcp_type.

        Args:
            mcp_type: "resource", "tool", or "prompt"
            resource_uri: URI or name of resource/tool/prompt
            server_url: MCP server URL
            input_data: Input data/arguments
            auth_token: Optional authentication token
            http_fallback_pattern: Custom HTTP endpoint pattern for fallback
                                   (default: /tools/{tool_name})

        Returns:
            MCPResult with operation result

        Example:
            # Read a resource
            result = await mcp.execute(
                mcp_type="resource",
                resource_uri="file:///data/config.json",
                server_url="http://server:3000/sse"
            )

            # Call a tool
            result = await mcp.execute(
                mcp_type="tool",
                resource_uri="search",
                server_url="http://server:3000/sse",
                input_data={"query": "python"}
            )

            # Call a tool with custom HTTP fallback pattern
            result = await mcp.execute(
                mcp_type="tool",
                resource_uri="search",
                server_url="http://server:3000",
                input_data={"query": "python"},
                http_fallback_pattern="/api/v1/mcp/tools/{tool_name}/execute"
            )
        """
        if not server_url:
            return MCPResult(
                success=False,
                result=None,
                error="MCP server URL is required"
            )

        mcp_type_lower = mcp_type.lower()

        try:
            if mcp_type_lower == MCPType.RESOURCE:
                return await self.read_resource(server_url, resource_uri, auth_token)
            elif mcp_type_lower == MCPType.TOOL:
                return await self.call_tool(server_url, resource_uri, input_data, auth_token)
            elif mcp_type_lower == MCPType.PROMPT:
                return await self.get_prompt(server_url, resource_uri, input_data, auth_token)
            else:
                return MCPResult(
                    success=False,
                    result=None,
                    error=f"Unknown MCP type: {mcp_type}. Valid: resource, tool, prompt"
                )
        except Exception as e:
            # Fallback to HTTP for tool calls if FastMCP fails
            if mcp_type_lower == MCPType.TOOL:
                logger.info(f"FastMCP failed, trying HTTP fallback: {e}")
                return await self._http_call_tool(
                    server_url,
                    resource_uri,
                    input_data,
                    auth_token,
                    http_fallback_pattern
                )
            return MCPResult(success=False, result=None, error=str(e))


# =============================================================================
# Global Instance
# =============================================================================

mcp_service = MCPService()
