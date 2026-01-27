# MCP Implementation Guide - FastMCP

This document provides a comprehensive guide for implementing Model Context Protocol (MCP) support in AgentStudio using **FastMCP** - a simple, decorator-based framework.

---

## Table of Contents

1. [Overview](#overview)
2. [Why FastMCP?](#why-fastmcp)
3. [Architecture](#architecture)
4. [Installation](#installation)
5. [Implementation](#implementation)
6. [How MCP Tools Work in AgentStudio Workflow](#how-mcp-tools-work-in-agentstudio-workflow)
7. [API Reference](#api-reference)
8. [Building MCP Servers](#building-mcp-servers)
9. [Client Usage Examples](#client-usage-examples)
10. [Integration with AgentStudio](#integration-with-agentstudio)
11. [Testing](#testing)
12. [Deployment](#deployment)
13. [Troubleshooting](#troubleshooting)

---

## Overview

### What is MCP?

**Model Context Protocol (MCP)** is an open protocol developed by Anthropic that standardizes how AI applications connect to external data sources and tools. Think of it as "the USB-C port for AI" - a uniform way to connect LLMs to resources they can use.

```
┌──────────────┐         ┌─────────────┐         ┌──────────────┐
│   AI Agent   │ ──MCP── │  MCP Server │ ──────▶ │  Data Source │
│ (AgentStudio)│         │  (FastMCP)  │         │  (Files/DB)  │
└──────────────┘         └─────────────┘         └──────────────┘
```

### Three MCP Primitives

| Primitive | Direction | Purpose | Example |
|-----------|-----------|---------|---------|
| **Resources** | Server → Client | Read-only data access (like GET) | Files, DB records, API data |
| **Tools** | Client → Server | Execute actions (like POST) | Run queries, write files |
| **Prompts** | Server → Client | Reusable templates | System prompts, few-shot examples |

---

## Why FastMCP?

### Version Information

| Attribute | Value |
|-----------|-------|
| **Latest Stable** | 2.14.4 (Jan 2026) |
| **Beta** | 3.0.0b1 |
| **Python Requirement** | ≥3.10 |
| **License** | Apache 2.0 |
| **GitHub** | [jlowin/fastmcp](https://github.com/jlowin/fastmcp) |
| **Documentation** | [gofastmcp.com](https://gofastmcp.com) |

### Comparison

| Feature | Official `mcp` SDK | **FastMCP** |
|---------|-------------------|-------------|
| **Syntax** | Verbose, class-based | Simple, decorator-based |
| **Learning Curve** | Steeper | Like FastAPI - intuitive |
| **Server Creation** | Complex setup | 5 lines of code |
| **Type Safety** | Manual | Automatic from type hints |
| **Client Library** | Separate | Built-in |
| **Auth Support** | Basic | Enterprise (OAuth, Azure, Auth0) |
| **Transports** | Limited | HTTP, SSE, STDIO built-in |

### FastMCP Advantages

```python
# Official MCP SDK - Verbose
class MyServer(Server):
    def __init__(self):
        super().__init__("my-server")

    async def list_tools(self):
        return [Tool(name="search", ...)]

    async def call_tool(self, name, args):
        if name == "search":
            return self._search(args)

# FastMCP - Simple & Clean
from fastmcp import FastMCP

mcp = FastMCP("my-server")

@mcp.tool()
def search(query: str) -> str:
    """Search for something."""
    return do_search(query)
```

---

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AgentStudio Platform                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌────────────────┐    ┌───────────────────┐   │
│  │  Frontend    │    │   Backend API  │    │   MCP Client      │   │
│  │  (React)     │───▶│   (FastAPI)    │───▶│   (FastMCP)       │   │
│  └──────────────┘    └────────────────┘    └───────────────────┘   │
│                                                      │              │
└──────────────────────────────────────────────────────│──────────────┘
                                                       │
                       ┌───────────────────────────────┼───────────────┐
                       │                               │               │
                       ▼                               ▼               ▼
              ┌─────────────────┐            ┌─────────────────┐  ┌─────────────┐
              │  FastMCP Server │            │  FastMCP Server │  │  Any MCP    │
              │  (File System)  │            │  (Database)     │  │  Server     │
              └─────────────────┘            └─────────────────┘  └─────────────┘
```

### Transport Options

| Transport | Use Case | URL Format | Recommendation |
|-----------|----------|------------|----------------|
| **Streamable HTTP** | Modern HTTP servers | `http://server:port/mcp` | **Recommended for new deployments** |
| **SSE** | Remote HTTP server | `http://server:port/sse` | Backward compatibility |
| **STDIO** | Local subprocess | Command + args | Development/local tools |

---

## Installation

### Add to Requirements

**File: `backend/requirements.txt`**

```txt
# MCP (Model Context Protocol) - FastMCP
# For production stability, pin to v2
fastmcp<3
```

### Install

```bash
cd backend
pip install 'fastmcp<3'

# Or for latest (may include beta features)
pip install fastmcp
```

### Verify Installation

```bash
python -c "import fastmcp; print(fastmcp.__version__)"
# Expected output: 2.14.4 (or similar 2.x version)
```

---

## Implementation

### File Structure

```
backend/app/services/
├── mcp_service.py      # MCP client service (connects to servers)
├── code_executor.py    # Existing - Code execution
└── tools/              # Existing - Built-in tools

mcp_servers/            # Optional - Your own MCP servers
├── file_server.py
├── database_server.py
└── api_server.py
```

---

### MCP Client Service

**File: `backend/app/services/mcp_service.py`**

```python
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

import asyncio
import httpx
import json
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from contextlib import asynccontextmanager

# Try to import FastMCP client
try:
    from fastmcp import Client
    from fastmcp.client.transports import SSETransport, StreamableHttpTransport
    from fastmcp.client.auth import BearerAuth
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


class MCPService:
    """
    FastMCP Client Service for connecting to MCP servers.

    Supports:
    - Reading resources (files, data)
    - Calling tools (functions, actions)
    - Getting prompts (templates)

    Example:
        mcp = MCPService()

        # Call a tool
        result = await mcp.call_tool(
            server_url="http://localhost:3000/sse",
            tool_name="search",
            arguments={"query": "python"}
        )
    """

    DEFAULT_TIMEOUT = 30

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        self.timeout = timeout

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
        Create a FastMCP client connection.

        Args:
            server_url: MCP server URL (SSE or HTTP endpoint)
            auth_token: Optional Bearer token for authentication
            headers: Optional additional headers

        Yields:
            Connected FastMCP Client
        """
        if not FASTMCP_AVAILABLE:
            raise RuntimeError("FastMCP not installed. Run: pip install 'fastmcp<3'")

        # Build headers
        request_headers = headers or {}

        # Determine transport based on URL
        if server_url.startswith("http"):
            if "/sse" in server_url:
                # SSE Transport (backward compatibility)
                transport = SSETransport(
                    url=server_url,
                    headers=request_headers
                )
            else:
                # Streamable HTTP Transport (recommended)
                transport = StreamableHttpTransport(
                    url=server_url,
                    headers=request_headers
                )
        else:
            raise ValueError(f"Unsupported URL scheme: {server_url}. Use http:// or https://")

        # Create client with optional auth
        if auth_token:
            client = Client(transport, auth=BearerAuth(auth_token))
        else:
            client = Client(transport)

        async with client:
            yield client

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

        Example:
            result = await mcp.list_resources("http://server:3000/sse")
            # Returns:
            # {
            #   "resources": [
            #     {"uri": "file:///data/config.json", "name": "Config"},
            #     {"uri": "db://users", "name": "Users Table"}
            #   ]
            # }
        """
        start_time = time.time()
        try:
            async with self._get_client(server_url, auth_token) as client:
                resources = await client.list_resources()
                return MCPResult(
                    success=True,
                    result={
                        "resources": [
                            {
                                "uri": str(r.uri),
                                "name": r.name,
                                "description": getattr(r, 'description', None),
                                "mimeType": getattr(r, 'mimeType', None)
                            }
                            for r in resources
                        ]
                    },
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

        Example:
            result = await mcp.read_resource(
                "http://server:3000/sse",
                "file:///data/config.json"
            )
            # Returns: {"contents": [{"uri": "...", "text": "..."}]}
        """
        start_time = time.time()
        try:
            async with self._get_client(server_url, auth_token) as client:
                content = await client.read_resource(resource_uri)

                # Handle different response formats
                if isinstance(content, list):
                    contents = [
                        {
                            "uri": resource_uri,
                            "text": getattr(c, 'text', str(c)),
                            "mimeType": getattr(c, 'mimeType', None)
                        }
                        for c in content
                    ]
                else:
                    contents = [{
                        "uri": resource_uri,
                        "text": getattr(content, 'text', str(content)),
                        "mimeType": getattr(content, 'mimeType', None)
                    }]

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

        Example:
            result = await mcp.list_tools("http://server:3000/sse")
            # Returns:
            # {
            #   "tools": [
            #     {
            #       "name": "query_database",
            #       "description": "Execute SQL query",
            #       "inputSchema": {"type": "object", ...}
            #     }
            #   ]
            # }
        """
        start_time = time.time()
        try:
            async with self._get_client(server_url, auth_token) as client:
                tools = await client.list_tools()
                return MCPResult(
                    success=True,
                    result={
                        "tools": [
                            {
                                "name": t.name,
                                "description": getattr(t, 'description', None),
                                "inputSchema": getattr(t, 'inputSchema', {})
                            }
                            for t in tools
                        ]
                    },
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

        Example:
            result = await mcp.call_tool(
                server_url="http://server:3000/sse",
                tool_name="query_database",
                arguments={"query": "SELECT * FROM users"}
            )
            # Returns: {"content": [{"type": "text", "text": "[{...}]"}]}
        """
        start_time = time.time()
        try:
            async with self._get_client(server_url, auth_token) as client:
                result = await client.call_tool(tool_name, arguments or {})

                # Parse result - FastMCP returns result with .data attribute
                if hasattr(result, 'data'):
                    content = [{"type": "text", "text": str(result.data)}]
                elif hasattr(result, 'content'):
                    content = [
                        {
                            "type": getattr(c, 'type', 'text'),
                            "text": getattr(c, 'text', str(c))
                        }
                        for c in result.content
                    ]
                else:
                    content = [{"type": "text", "text": str(result)}]

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
        try:
            async with self._get_client(server_url, auth_token) as client:
                prompts = await client.list_prompts()
                return MCPResult(
                    success=True,
                    result={
                        "prompts": [
                            {
                                "name": p.name,
                                "description": getattr(p, 'description', None),
                                "arguments": getattr(p, 'arguments', [])
                            }
                            for p in prompts
                        ]
                    },
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
        try:
            async with self._get_client(server_url, auth_token) as client:
                result = await client.get_prompt(prompt_name, arguments or {})
                return MCPResult(
                    success=True,
                    result={
                        "messages": [
                            {
                                "role": m.role,
                                "content": str(m.content)
                            }
                            for m in result.messages
                        ]
                    },
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
        auth_token: str = None
    ) -> MCPResult:
        """
        Fallback HTTP-based tool call for simple MCP servers.
        """
        start_time = time.time()
        try:
            headers = {"Content-Type": "application/json"}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Standard MCP HTTP endpoint pattern
                endpoint = f"{server_url.rstrip('/')}/tools/{tool_name}"

                response = await client.post(
                    endpoint,
                    json={"arguments": arguments or {}},
                    headers=headers
                )

                if response.status_code == 200:
                    return MCPResult(
                        success=True,
                        result=response.json(),
                        execution_time_ms=int((time.time() - start_time) * 1000)
                    )
                else:
                    return MCPResult(
                        success=False,
                        result=None,
                        error=f"HTTP {response.status_code}: {response.text}",
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
        auth_token: str = None
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
        """
        if not server_url:
            return MCPResult(
                success=False,
                result=None,
                error="MCP server URL is required"
            )

        mcp_type = mcp_type.lower()

        try:
            if mcp_type == MCPType.RESOURCE:
                return await self.read_resource(server_url, resource_uri, auth_token)
            elif mcp_type == MCPType.TOOL:
                return await self.call_tool(server_url, resource_uri, input_data, auth_token)
            elif mcp_type == MCPType.PROMPT:
                return await self.get_prompt(server_url, resource_uri, input_data, auth_token)
            else:
                return MCPResult(
                    success=False,
                    result=None,
                    error=f"Unknown MCP type: {mcp_type}. Valid: resource, tool, prompt"
                )
        except Exception as e:
            # Fallback to HTTP for tool calls if FastMCP fails
            if mcp_type == MCPType.TOOL:
                logger.info(f"FastMCP failed, trying HTTP fallback: {e}")
                return await self._http_call_tool(server_url, resource_uri, input_data, auth_token)
            return MCPResult(success=False, result=None, error=str(e))


# =============================================================================
# Global Instance
# =============================================================================

mcp_service = MCPService()
```

---

## How MCP Tools Work in AgentStudio Workflow

This section explains how MCP tools integrate with the AgentStudio agent workflow and how they are executed during agent runs.

### Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AgentStudio Workflow                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. USER INPUT                                                              │
│     ↓                                                                       │
│  2. LLM AGENT ──────────────────────────────────────────────────────────┐   │
│     │                                                                   │   │
│     │  Decides which tool to use based on:                              │   │
│     │  - User query                                                     │   │
│     │  - Available tools (built-in, custom, api, mcp)                   │   │
│     │  - Tool descriptions                                              │   │
│     ↓                                                                   │   │
│  3. TOOL ROUTER                                                         │   │
│     │                                                                   │   │
│     ├── type="built-in" → Execute Python function directly              │   │
│     ├── type="custom"   → Execute user code via code_executor           │   │
│     ├── type="api"      → HTTP call to external API                     │   │
│     └── type="mcp"      → FastMCP client call to MCP server ←───────────┘   │
│           │                                                                 │
│           ↓                                                                 │
│  4. MCP SERVICE                                                             │
│     │                                                                       │
│     │  ┌─────────────────────────────────────────────────────────────────┐  │
│     │  │  FastMCP Client                                                 │  │
│     │  │                                                                 │  │
│     │  │  - Connect to MCP server (SSE/HTTP)                             │  │
│     │  │  - Call tool with arguments                                     │  │
│     │  │  - Return result to LangGraph                                   │  │
│     │  └─────────────────────────────────────────────────────────────────┘  │
│     ↓                                                                       │
│  5. RESULT → Back to LLM Agent for processing                               │
│     ↓                                                                       │
│  6. OUTPUT → Final response to user                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Step-by-Step Flow

#### Step 1: Create MCP Tool in AgentStudio

In the UI, user creates an MCP tool with configuration:

```json
{
  "name": "database_query",
  "type": "mcp",
  "description": "Query the customer database",
  "config": {
    "mcp_type": "tool",
    "mcp_server_url": "http://mcp-database:3000/sse",
    "resource_uri": "query",
    "parameters": {
      "sql": {
        "type": "string",
        "description": "SQL query to execute",
        "required": true
      }
    },
    "auth_token": "optional-bearer-token"
  }
}
```

#### Step 2: Agent Builder - Add MCP Tool to Agent

In the visual agent builder:

```
┌─────────┐     ┌───────────┐     ┌──────────────────┐     ┌────────┐
│  INPUT  │────▶│ LLM_AGENT │────▶│ TOOL (MCP:       │────▶│ OUTPUT │
│         │     │           │     │  database_query) │     │        │
└─────────┘     └───────────┘     └──────────────────┘     └────────┘
```

The agent configuration includes the MCP tool in its available tools:

```json
{
  "nodes": [
    {"id": "input", "type": "INPUT"},
    {"id": "agent", "type": "LLM_AGENT", "tools": ["database_query"]},
    {"id": "tool", "type": "TOOL", "tool_id": "mcp-tool-uuid"},
    {"id": "output", "type": "OUTPUT"}
  ]
}
```

#### Step 3: Agent Execution - LangGraph Engine

When the agent runs, the LangGraph engine processes the workflow:

**File: `backend/app/services/langgraph_engine.py`**

```python
async def execute_tool_node(state: AgentState, config: dict):
    """Execute a tool node in the workflow."""
    tool = get_tool_by_id(state.current_tool_id)

    if tool.type == "mcp":
        # Use MCP service to execute
        from app.services.mcp_service import mcp_service

        result = await mcp_service.execute(
            mcp_type=tool.config.get("mcp_type", "tool"),
            resource_uri=tool.config.get("resource_uri"),
            server_url=tool.config.get("mcp_server_url"),
            input_data=state.tool_input,
            auth_token=tool.config.get("auth_token")
        )

        return {
            "tool_result": result.result,
            "tool_error": result.error,
            "execution_time": result.execution_time_ms
        }
```

#### Step 4: MCP Server Receives Request

The external MCP server (running FastMCP) receives the tool call:

```python
# MCP Server (external)
from fastmcp import FastMCP

mcp = FastMCP("Database Server")

@mcp.tool()
async def query(sql: str) -> list[dict]:
    """Execute SQL query."""
    # Connect to database and execute
    results = await db.fetch(sql)
    return [dict(row) for row in results]
```

#### Step 5: Result Returns Through the Chain

```
MCP Server Response
        ↓
FastMCP Client (mcp_service.py)
        ↓
LangGraph Engine (tool result)
        ↓
LLM Agent (processes result)
        ↓
Output Node (formats response)
        ↓
User sees final answer
```

### Example: Complete Agent with MCP Tool

**User Query:** "How many active customers do we have?"

**Agent Flow:**

1. **INPUT Node**: Receives "How many active customers do we have?"

2. **LLM_AGENT Node**:
   - Sees available tools: `[calculator, datetime, database_query]`
   - Decides to use `database_query` tool
   - Generates arguments: `{"sql": "SELECT COUNT(*) as count FROM customers WHERE status = 'active'"}`

3. **TOOL Node** (MCP):
   - Tool type is `mcp`
   - Calls `mcp_service.execute()`:
     ```python
     result = await mcp_service.execute(
         mcp_type="tool",
         resource_uri="query",
         server_url="http://mcp-database:3000/sse",
         input_data={"sql": "SELECT COUNT(*) as count FROM customers WHERE status = 'active'"}
     )
     # result.result = {"content": [{"type": "text", "text": "[{\"count\": 1523}]"}]}
     ```

4. **LLM_AGENT Node** (receives result):
   - Processes: `[{"count": 1523}]`
   - Generates response: "You have 1,523 active customers."

5. **OUTPUT Node**: Returns final response to user

### MCP Tool Configuration Schema

When creating an MCP tool in the UI, these fields are available:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Tool name (used by LLM) |
| `description` | string | Yes | What the tool does (LLM uses this to decide) |
| `mcp_type` | enum | Yes | `tool`, `resource`, or `prompt` |
| `mcp_server_url` | string | Yes | MCP server endpoint URL |
| `resource_uri` | string | Yes | Tool/resource name on the MCP server |
| `parameters` | object | No | Input parameters schema |
| `auth_token` | string | No | Bearer token for authentication |
| `timeout` | number | No | Request timeout in seconds (default: 30) |

### Testing MCP Tools from UI

1. **Go to Tools Page** → MCP Tools tab
2. **Click "Test"** on an MCP tool
3. **Enter parameters** in the form
4. **Click "Execute"**
5. **View result** in the response panel

The test endpoint calls:
```
POST /api/v1/tools/{tool_id}/test
{
  "input_data": {"sql": "SELECT * FROM users LIMIT 5"}
}
```

Which internally calls:
```python
result = await mcp_service.execute(
    mcp_type=tool.config["mcp_type"],
    resource_uri=tool.config["resource_uri"],
    server_url=tool.config["mcp_server_url"],
    input_data=request.input_data
)
```

### MCP Tool in Agent Execution (Full Example)

**API Call:**
```
POST /api/v1/execute/{agent_id}
{
  "input": "What customers signed up this week?"
}
```

**LangGraph Execution Trace:**
```
[INPUT] → state.query = "What customers signed up this week?"
    ↓
[LLM_AGENT] → Selects tool: database_query
             → Generates: {"sql": "SELECT * FROM customers WHERE created_at > NOW() - INTERVAL '7 days'"}
    ↓
[TOOL:mcp] → mcp_service.call_tool(
               server_url="http://mcp-db:3000/sse",
               tool_name="query",
               arguments={"sql": "..."}
             )
    ↓
[MCP_SERVER] → Executes query, returns results
    ↓
[LLM_AGENT] → Processes results, generates response
    ↓
[OUTPUT] → "This week, 47 new customers signed up: ..."
```

---

## API Reference

### MCPService Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `list_resources(server_url)` | List available resources | `MCPResult` |
| `read_resource(server_url, uri)` | Read a resource | `MCPResult` |
| `list_tools(server_url)` | List available tools | `MCPResult` |
| `call_tool(server_url, name, args)` | Execute a tool | `MCPResult` |
| `list_prompts(server_url)` | List available prompts | `MCPResult` |
| `get_prompt(server_url, name, args)` | Get a prompt template | `MCPResult` |
| `execute(mcp_type, uri, url, data)` | Main entry point | `MCPResult` |

### MCPResult Structure

```python
@dataclass
class MCPResult:
    success: bool           # True if operation succeeded
    result: Any             # Operation result data
    error: Optional[str]    # Error message if failed
    execution_time_ms: int  # Execution time in milliseconds
```

---

## Building MCP Servers

### Example 1: File System Server

**File: `mcp_servers/file_server.py`**

```python
"""
File System MCP Server using FastMCP

Run: fastmcp run file_server.py --transport sse --port 3000
"""

from fastmcp import FastMCP
import os

mcp = FastMCP("File Server")


@mcp.resource("file://{path}")
def read_file(path: str) -> str:
    """Read a file from the filesystem."""
    with open(path, 'r') as f:
        return f.read()


@mcp.tool()
def list_files(directory: str = ".") -> list[str]:
    """List files in a directory."""
    return os.listdir(directory)


@mcp.tool()
def search_files(pattern: str, directory: str = ".") -> list[str]:
    """Search for files matching a pattern."""
    import glob
    return glob.glob(os.path.join(directory, pattern), recursive=True)


@mcp.tool()
def get_file_info(path: str) -> dict:
    """Get file metadata."""
    stat = os.stat(path)
    return {
        "size": stat.st_size,
        "modified": stat.st_mtime,
        "is_file": os.path.isfile(path),
        "is_dir": os.path.isdir(path)
    }


if __name__ == "__main__":
    mcp.run()
```

**Run it:**
```bash
# Development (stdio)
python file_server.py

# Production (SSE server)
fastmcp run file_server.py --transport sse --port 3000
```

---

### Example 2: Database Server

**File: `mcp_servers/database_server.py`**

```python
"""
Database MCP Server using FastMCP

Provides SQL query capabilities via MCP.
"""

from fastmcp import FastMCP
import asyncpg
import os

mcp = FastMCP("Database Server")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/mydb")


@mcp.tool()
async def query(sql: str, params: list = None) -> list[dict]:
    """
    Execute a SQL query and return results.

    Args:
        sql: SQL query to execute
        params: Query parameters (optional)

    Returns:
        List of rows as dictionaries
    """
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch(sql, *(params or []))
        return [dict(row) for row in rows]
    finally:
        await conn.close()


@mcp.tool()
async def get_tables() -> list[str]:
    """List all tables in the database."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
        """)
        return [row['table_name'] for row in rows]
    finally:
        await conn.close()


@mcp.tool()
async def describe_table(table_name: str) -> list[dict]:
    """Get column information for a table."""
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        rows = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = $1
            ORDER BY ordinal_position
        """, table_name)
        return [dict(row) for row in rows]
    finally:
        await conn.close()


@mcp.resource("db://tables")
async def list_all_tables() -> str:
    """Resource: List of all database tables."""
    tables = await get_tables()
    return "\n".join(tables)


if __name__ == "__main__":
    mcp.run()
```

---

### Example 3: API Integration Server

**File: `mcp_servers/api_server.py`**

```python
"""
External API MCP Server using FastMCP

Provides access to external APIs via MCP.
"""

from fastmcp import FastMCP
import httpx

mcp = FastMCP("API Server")


@mcp.tool()
async def fetch_url(url: str, method: str = "GET", headers: dict = None) -> dict:
    """
    Fetch data from a URL.

    Args:
        url: URL to fetch
        method: HTTP method (GET, POST, etc.)
        headers: Optional headers

    Returns:
        Response data
    """
    async with httpx.AsyncClient() as client:
        response = await client.request(method, url, headers=headers)
        return {
            "status": response.status_code,
            "headers": dict(response.headers),
            "body": response.text
        }


@mcp.tool()
async def get_weather(city: str) -> dict:
    """Get current weather for a city."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://wttr.in/{city}?format=j1"
        )
        data = response.json()
        current = data['current_condition'][0]
        return {
            "city": city,
            "temperature_c": current['temp_C'],
            "temperature_f": current['temp_F'],
            "condition": current['weatherDesc'][0]['value'],
            "humidity": current['humidity']
        }


@mcp.tool()
async def search_github(query: str, language: str = None) -> list[dict]:
    """Search GitHub repositories."""
    q = query
    if language:
        q += f" language:{language}"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/search/repositories",
            params={"q": q, "per_page": 10}
        )
        data = response.json()
        return [
            {
                "name": repo['full_name'],
                "description": repo['description'],
                "stars": repo['stargazers_count'],
                "url": repo['html_url']
            }
            for repo in data.get('items', [])
        ]


@mcp.prompt()
def api_request_template(method: str, url: str) -> str:
    """Template for making API requests."""
    return f"""
    Make an HTTP {method} request to: {url}

    Please analyze the response and provide:
    1. Status code interpretation
    2. Key data points
    3. Any errors or issues
    """


if __name__ == "__main__":
    mcp.run()
```

---

## Integration with AgentStudio

### Update Tools Endpoint

**File: `backend/app/api/v1/tools.py`**

```python
# Add import at top
from app.services.mcp_service import mcp_service

# Update the MCP section in test_tool endpoint:

elif tool.type == "mcp":
    # Execute MCP operation using FastMCP client
    mcp_type = tool.config.get("mcp_type", "tool")
    resource_uri = tool.config.get("resource_uri", "")
    server_url = tool.config.get("mcp_server_url", "")
    auth_token = tool.config.get("auth_token")

    if not server_url:
        return ToolExecuteResponse(
            success=False,
            result=None,
            error="MCP server URL is required. Configure it in the tool settings."
        )

    result = await mcp_service.execute(
        mcp_type=mcp_type,
        resource_uri=resource_uri,
        server_url=server_url,
        input_data=request.input_data,
        auth_token=auth_token
    )

    return ToolExecuteResponse(
        success=result.success,
        result=result.result,
        error=result.error,
        execution_time=result.execution_time_ms
    )
```

---

## Client Usage Examples

### From Python

```python
from app.services.mcp_service import mcp_service

# List available tools
tools = await mcp_service.list_tools("http://localhost:3000/sse")
print(tools.result)

# Call a tool
result = await mcp_service.call_tool(
    server_url="http://localhost:3000/sse",
    tool_name="search_files",
    arguments={"pattern": "*.py", "directory": "/src"}
)
print(result.result)

# Read a resource
content = await mcp_service.read_resource(
    server_url="http://localhost:3000/sse",
    resource_uri="file:///config/settings.json"
)
print(content.result)
```

### From UI (AgentStudio)

1. **Create MCP Tool:**
   - Go to Tools → MCP Tools → Create MCP Tool
   - Fill in:
     - Name: `db_query`
     - MCP Type: `tool`
     - Resource URI: `query`
     - Server URL: `http://mcp-server:3000/sse`

2. **Test:**
   - Click Test on the tool
   - Enter parameters: `{"sql": "SELECT * FROM users"}`
   - Click Execute

---

## Deployment

### Docker Compose Setup

**File: `docker-compose.mcp.yml`**

```yaml
version: '3.8'

services:
  # FastMCP File Server
  mcp-files:
    build:
      context: ./mcp_servers
      dockerfile: Dockerfile
    command: fastmcp run file_server.py --transport sse --port 3000
    ports:
      - "3001:3000"
    volumes:
      - ./data:/data:ro
    environment:
      - MCP_SERVER_NAME=file-server

  # FastMCP Database Server
  mcp-database:
    build:
      context: ./mcp_servers
      dockerfile: Dockerfile
    command: fastmcp run database_server.py --transport sse --port 3000
    ports:
      - "3002:3000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/mydb
    depends_on:
      - postgres

  # FastMCP API Server
  mcp-api:
    build:
      context: ./mcp_servers
      dockerfile: Dockerfile
    command: fastmcp run api_server.py --transport sse --port 3000
    ports:
      - "3003:3000"
```

### Dockerfile for MCP Servers

**File: `mcp_servers/Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install 'fastmcp<3' httpx asyncpg

COPY *.py .

EXPOSE 3000

CMD ["fastmcp", "run", "file_server.py", "--transport", "sse", "--port", "3000"]
```

---

## Testing

### Unit Tests

```python
import pytest
from app.services.mcp_service import mcp_service, MCPResult

@pytest.mark.asyncio
async def test_call_tool():
    """Test calling an MCP tool."""
    result = await mcp_service.call_tool(
        server_url="http://localhost:3000/sse",
        tool_name="list_files",
        arguments={"directory": "/tmp"}
    )

    assert result.success
    assert "content" in result.result

@pytest.mark.asyncio
async def test_missing_server_url():
    """Test error handling for missing URL."""
    result = await mcp_service.execute(
        mcp_type="tool",
        resource_uri="test",
        server_url=""
    )

    assert not result.success
    assert "required" in result.error.lower()
```

### Integration Test

```bash
# Start test MCP server
fastmcp run file_server.py --transport sse --port 3000 &

# Run tests
pytest tests/test_mcp_service.py -v

# Cleanup
pkill -f "fastmcp run"
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `FastMCP not installed` | Missing package | `pip install 'fastmcp<3'` |
| `Connection refused` | Server not running | Start MCP server first |
| `SSE connection failed` | Wrong URL | Use `/sse` endpoint for SSE transport |
| `Tool not found` | Wrong tool name | Check `list_tools()` output |
| `Timeout` | Slow operation | Increase timeout in config |
| `Python version error` | Python < 3.10 | Upgrade to Python 3.10+ |

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or for just MCP
logging.getLogger("fastmcp").setLevel(logging.DEBUG)
```

### Test Connection

```python
async def test_connection(server_url: str):
    """Quick connectivity test."""
    result = await mcp_service.list_tools(server_url)
    if result.success:
        print(f"Connected! Found {len(result.result['tools'])} tools")
        for tool in result.result['tools']:
            print(f"  - {tool['name']}: {tool.get('description', 'No description')}")
    else:
        print(f"Failed: {result.error}")
```

---

## Summary

### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `requirements.txt` | Modify | Add `fastmcp<3` |
| `mcp_service.py` | Create | FastMCP client service |
| `tools.py` | Modify | Update MCP execution block |
| `mcp_servers/*.py` | Create | Optional MCP servers |

### Quick Start Commands

```bash
# Install FastMCP
pip install 'fastmcp<3'

# Create a simple MCP server
cat > my_server.py << 'EOF'
from fastmcp import FastMCP

mcp = FastMCP("My Server")

@mcp.tool()
def hello(name: str) -> str:
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run()
EOF

# Run it
fastmcp run my_server.py --transport sse --port 3000

# Test from another terminal
curl http://localhost:3000/sse
```

---

## References

- [FastMCP GitHub](https://github.com/jlowin/fastmcp)
- [FastMCP Documentation](https://gofastmcp.com)
- [FastMCP PyPI](https://pypi.org/project/fastmcp/)
- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [Client Transports Guide](https://gofastmcp.com/clients/transports)

---

*Last Updated: January 2026*
*AgentStudio Version: 1.0.0-beta*
*FastMCP Version: 2.14.x (stable)*
