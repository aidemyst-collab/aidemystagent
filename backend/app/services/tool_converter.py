"""
Tool Converter - Converts database tools to LangChain-compatible format
"""
from typing import List, Any, Dict, Optional
from langchain_core.tools import tool
from app.models.tool import Tool, ToolType
from app.services.tools import tool_registry, APIIntegrationTool


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
        """Convert MCP tool to LangChain format."""
        # TODO: Implement MCP tool execution

        async def mcp_tool_func(**kwargs) -> str:
            return "MCP tool execution not yet implemented"

        mcp_tool_func.__name__ = db_tool.name
        mcp_tool_func.__doc__ = db_tool.description

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
