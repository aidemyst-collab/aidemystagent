"""
Tool Converter - Converts database tools to LangChain-compatible format
"""
import json
import logging
from typing import List, Any, Dict, Optional
from langchain_core.tools import tool
from app.models.tool import Tool, ToolType
from app.services.tools import tool_registry, APIIntegrationTool
from app.services.mcp_service import mcp_service

logger = logging.getLogger(__name__)


class ToolConverter:
    """Convert database tools to LangChain tools."""

    @staticmethod
    def convert_to_langchain_tool(db_tool: Tool) -> Any:
        """
        Convert a database tool to LangChain tool format.

        Args:
            db_tool: Tool from database

        Returns:
            LangChain-compatible tool
        """
        if db_tool.type == ToolType.BUILT_IN:
            return ToolConverter._convert_builtin_tool(db_tool)
        elif db_tool.type == ToolType.API:
            return ToolConverter._convert_api_tool(db_tool)
        elif db_tool.type == ToolType.CUSTOM:
            return ToolConverter._convert_custom_tool(db_tool)
        elif db_tool.type == ToolType.MCP:
            return ToolConverter._convert_mcp_tool(db_tool)
        else:
            raise ValueError(f"Unknown tool type: {db_tool.type}")

    @staticmethod
    def _convert_builtin_tool(db_tool: Tool) -> Any:
        """Convert built-in tool to LangChain format."""
        # Get the built-in tool from registry
        builtin_tool = tool_registry.get_tool(db_tool.name)
        if not builtin_tool:
            raise ValueError(f"Built-in tool not found: {db_tool.name}")

        # Create a LangChain tool wrapper
        async def tool_func(**kwargs) -> str:
            result = await builtin_tool.execute(kwargs)
            if result.success:
                return str(result.result)
            else:
                return f"Error: {result.error}"

        tool_func.__name__ = db_tool.name
        tool_func.__doc__ = db_tool.description

        return tool(tool_func)

    @staticmethod
    def _convert_api_tool(db_tool: Tool) -> Any:
        """Convert API integration tool to LangChain format."""
        api_config = db_tool.config.get("api", {})

        # Create API tool instance
        api_tool = APIIntegrationTool(
            name=db_tool.name,
            description=db_tool.description,
            endpoint=api_config.get("endpoint"),
            method=api_config.get("method", "GET"),
            auth_type=api_config.get("auth_type", "none"),
            headers=api_config.get("headers", {}),
            timeout=api_config.get("timeout", 30)
        )

        # Create LangChain tool wrapper
        async def api_tool_func(**kwargs) -> str:
            result = await api_tool.execute(kwargs)
            if result.success:
                return str(result.result)
            else:
                return f"Error: {result.error}"

        api_tool_func.__name__ = db_tool.name
        api_tool_func.__doc__ = db_tool.description

        return tool(api_tool_func)

    @staticmethod
    def _convert_custom_tool(db_tool: Tool) -> Any:
        """Convert custom code tool to LangChain format."""
        # TODO: Implement custom code execution in sandbox

        async def custom_tool_func(**kwargs) -> str:
            return "Custom tool execution not yet implemented"

        custom_tool_func.__name__ = db_tool.name
        custom_tool_func.__doc__ = db_tool.description

        return tool(custom_tool_func)

    @staticmethod
    def _convert_mcp_tool(db_tool: Tool) -> Any:
        """
        Convert MCP tool to LangChain format.

        Extracts MCP configuration from db_tool.config and creates
        a LangChain tool that calls the MCP service.

        Expected config fields:
            - mcp_server_url: URL of the MCP server (required)
            - mcp_type: "tool", "resource", or "prompt" (default: "tool")
            - resource_uri: Tool name or resource URI (required)
            - auth_token: Optional authentication token
        """
        config = db_tool.config or {}

        # Extract MCP configuration
        server_url = config.get("mcp_server_url")
        mcp_type = config.get("mcp_type", "tool")
        resource_uri = config.get("resource_uri")
        auth_token = config.get("auth_token")

        # Validate required fields
        if not server_url:
            logger.warning(f"MCP tool {db_tool.name} missing mcp_server_url")
        if not resource_uri:
            logger.warning(f"MCP tool {db_tool.name} missing resource_uri")

        async def mcp_tool_func(**kwargs) -> str:
            """Execute MCP tool via mcp_service."""
            try:
                # Log the MCP tool call
                logger.info(
                    f"MCP tool call: {db_tool.name} | "
                    f"server={server_url} | type={mcp_type} | uri={resource_uri}"
                )

                # Validate configuration
                if not server_url:
                    return json.dumps({
                        "error": "MCP server URL not configured",
                        "tool": db_tool.name
                    })

                if not resource_uri:
                    return json.dumps({
                        "error": "MCP resource URI not configured",
                        "tool": db_tool.name
                    })

                # Call MCP service
                result = await mcp_service.execute(
                    mcp_type=mcp_type,
                    resource_uri=resource_uri,
                    server_url=server_url,
                    input_data=kwargs,
                    auth_token=auth_token
                )

                # Log result
                logger.info(
                    f"MCP tool result: {db_tool.name} | "
                    f"success={result.success} | time={result.execution_time_ms}ms"
                )

                # Return result
                if result.success:
                    # Extract content from result
                    if isinstance(result.result, dict):
                        # For tool calls, result has "content" key
                        if "content" in result.result:
                            content = result.result["content"]
                            # Extract text from content items
                            if isinstance(content, list) and len(content) > 0:
                                texts = [
                                    item.get("text", str(item))
                                    for item in content
                                    if isinstance(item, dict)
                                ]
                                return "\n".join(texts) if texts else json.dumps(content)
                        # For resources, result has "contents" key
                        elif "contents" in result.result:
                            contents = result.result["contents"]
                            if isinstance(contents, list) and len(contents) > 0:
                                texts = [
                                    item.get("text", str(item))
                                    for item in contents
                                    if isinstance(item, dict)
                                ]
                                return "\n".join(texts) if texts else json.dumps(contents)
                        # For prompts, result has "messages" key
                        elif "messages" in result.result:
                            return json.dumps(result.result["messages"])
                        # Default: return JSON
                        return json.dumps(result.result)
                    else:
                        return str(result.result)
                else:
                    error_msg = result.error or "Unknown MCP error"
                    logger.error(f"MCP tool error: {db_tool.name} | {error_msg}")
                    return json.dumps({
                        "error": error_msg,
                        "tool": db_tool.name,
                        "server": server_url
                    })

            except Exception as e:
                logger.exception(f"MCP tool exception: {db_tool.name} | {str(e)}")
                return json.dumps({
                    "error": str(e),
                    "tool": db_tool.name,
                    "type": "exception"
                })

        mcp_tool_func.__name__ = db_tool.name
        mcp_tool_func.__doc__ = db_tool.description or f"MCP tool: {db_tool.name}"

        return tool(mcp_tool_func)

    @staticmethod
    def convert_tools_list(db_tools: List[Tool]) -> List[Any]:
        """
        Convert a list of database tools to LangChain tools.

        Args:
            db_tools: List of tools from database

        Returns:
            List of LangChain-compatible tools
        """
        langchain_tools = []
        for db_tool in db_tools:
            try:
                langchain_tool = ToolConverter.convert_to_langchain_tool(db_tool)
                langchain_tools.append(langchain_tool)
            except Exception as e:
                # Log error but continue with other tools
                print(f"Error converting tool {db_tool.name}: {str(e)}")
                continue

        return langchain_tools
