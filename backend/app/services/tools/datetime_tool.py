from typing import Dict, Any
from datetime import datetime, timezone
import pytz
from .base import BaseTool, ToolOutput


class DateTimeTool(BaseTool):
    """Tool for date and time operations."""

    def __init__(self):
        super().__init__(
            name="datetime",
            description="Get current date, time, and timezone information. Supports timezone conversion."
        )

    async def execute(self, input_data: Dict[str, Any]) -> ToolOutput:
        """Execute date/time operation."""
        try:
            operation = input_data.get("operation", "current")
            tz_name = input_data.get("timezone", "UTC")

            if operation == "current":
                result = self._get_current_datetime(tz_name)
            elif operation == "timestamp":
                result = self._get_timestamp()
            elif operation == "format":
                date_str = input_data.get("date")
                format_str = input_data.get("format", "%Y-%m-%d %H:%M:%S")
                result = self._format_datetime(date_str, format_str, tz_name)
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

    def _get_current_datetime(self, tz_name: str) -> Dict[str, str]:
        """Get current date and time in specified timezone."""
        try:
            tz = pytz.timezone(tz_name)
        except:
            tz = pytz.UTC

        now = datetime.now(tz)

        return {
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "timezone": tz_name,
            "timestamp": int(now.timestamp()),
            "iso": now.isoformat(),
        }

    def _get_timestamp(self) -> int:
        """Get current Unix timestamp."""
        return int(datetime.now(timezone.utc).timestamp())

    def _format_datetime(self, date_str: str, format_str: str, tz_name: str) -> str:
        """Format datetime string."""
        try:
            tz = pytz.timezone(tz_name)
        except:
            tz = pytz.UTC

        dt = datetime.fromisoformat(date_str)
        dt = dt.replace(tzinfo=tz)

        return dt.strftime(format_str)

    def _get_parameters(self) -> Dict[str, Any]:
        """Get tool parameters schema."""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["current", "timestamp", "format"],
                    "description": "Operation to perform",
                    "default": "current"
                },
                "timezone": {
                    "type": "string",
                    "description": "Timezone name (e.g., 'America/New_York', 'UTC')",
                    "default": "UTC"
                },
                "date": {
                    "type": "string",
                    "description": "Date string in ISO format (for format operation)"
                },
                "format": {
                    "type": "string",
                    "description": "Output format string (for format operation)",
                    "default": "%Y-%m-%d %H:%M:%S"
                }
            },
            "required": []
        }
