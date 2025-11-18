from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel


class ToolInput(BaseModel):
    """Base class for tool inputs."""
    pass


class ToolOutput(BaseModel):
    """Base class for tool outputs."""
    success: bool
    result: Any
    error: Optional[str] = None


class BaseTool(ABC):
    """Base class for all tools."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> ToolOutput:
        """Execute the tool with given input."""
        pass

    def get_schema(self) -> Dict[str, Any]:
        """Get the tool's input schema."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self._get_parameters(),
        }

    @abstractmethod
    def _get_parameters(self) -> Dict[str, Any]:
        """Define the tool's parameters schema."""
        pass
