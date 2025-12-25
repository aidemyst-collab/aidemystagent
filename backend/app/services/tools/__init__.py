from typing import Dict
from .base import BaseTool
from .calculator import CalculatorTool
from .datetime_tool import DateTimeTool
from .json_parser import JSONParserTool
from .web_search import WebSearchTool
from .api_integration import APIIntegrationTool


class ToolRegistry:
    """Registry for all available tools."""

    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        """Register all built-in tools."""
        self.register_tool(CalculatorTool())
        self.register_tool(DateTimeTool())
        self.register_tool(JSONParserTool())
        self.register_tool(WebSearchTool())
        self.register_tool(APIIntegrationTool())

    def register_tool(self, tool: BaseTool):
        """Register a tool."""
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> BaseTool:
        """Get a tool by name."""
        return self.tools.get(name)

    def list_tools(self) -> list:
        """List all available tools."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "schema": tool.get_schema(),
            }
            for tool in self.tools.values()
        ]

    async def execute_tool(self, tool_name: str, input_data: dict):
        """Execute a tool by name."""
        tool = self.get_tool(tool_name)
        if not tool:
            return {
                "success": False,
                "result": None,
                "error": f"Tool not found: {tool_name}"
            }

        result = await tool.execute(input_data)
        return result.dict()


# Global tool registry instance
tool_registry = ToolRegistry()


__all__ = [
    "BaseTool",
    "CalculatorTool",
    "DateTimeTool",
    "JSONParserTool",
    "WebSearchTool",
    "APIIntegrationTool",
    "ToolRegistry",
    "tool_registry",
]
