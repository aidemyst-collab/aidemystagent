from typing import Dict, Any
import json
from .base import BaseTool, ToolOutput


class JSONParserTool(BaseTool):
    """Tool for parsing and manipulating JSON data."""

    def __init__(self):
        super().__init__(
            name="json_parser",
            description="Parse, validate, and extract data from JSON strings."
        )

    async def execute(self, input_data: Dict[str, Any]) -> ToolOutput:
        """Execute JSON operation."""
        try:
            operation = input_data.get("operation", "parse")
            json_string = input_data.get("json_string", "")

            if operation == "parse":
                result = self._parse_json(json_string)
            elif operation == "extract":
                path = input_data.get("path", "")
                result = self._extract_from_json(json_string, path)
            elif operation == "validate":
                result = self._validate_json(json_string)
            elif operation == "pretty":
                result = self._pretty_print(json_string)
            else:
                return ToolOutput(
                    success=False,
                    result=None,
                    error=f"Unknown operation: {operation}"
                )

            return ToolOutput(
                success=True,
                result=result,
                error=None
            )

        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=str(e)
            )

    def _parse_json(self, json_string: str) -> Dict[str, Any]:
        """Parse JSON string."""
        return json.loads(json_string)

    def _extract_from_json(self, json_string: str, path: str) -> Any:
        """Extract value from JSON using dot notation path."""
        data = json.loads(json_string)

        keys = path.split('.')
        result = data

        for key in keys:
            if isinstance(result, dict):
                result = result.get(key)
            elif isinstance(result, list) and key.isdigit():
                result = result[int(key)]
            else:
                raise ValueError(f"Invalid path: {path}")

        return result

    def _validate_json(self, json_string: str) -> Dict[str, Any]:
        """Validate JSON string."""
        try:
            json.loads(json_string)
            return {
                "valid": True,
                "message": "JSON is valid"
            }
        except json.JSONDecodeError as e:
            return {
                "valid": False,
                "message": str(e)
            }

    def _pretty_print(self, json_string: str) -> str:
        """Pretty print JSON."""
        data = json.loads(json_string)
        return json.dumps(data, indent=2, sort_keys=True)

    def _get_parameters(self) -> Dict[str, Any]:
        """Get tool parameters schema."""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["parse", "extract", "validate", "pretty"],
                    "description": "Operation to perform",
                    "default": "parse"
                },
                "json_string": {
                    "type": "string",
                    "description": "JSON string to process"
                },
                "path": {
                    "type": "string",
                    "description": "Dot notation path for extraction (e.g., 'user.name')"
                }
            },
            "required": ["json_string"]
        }
