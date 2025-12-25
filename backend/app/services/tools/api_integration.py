"""
API Integration Tool
Allows making HTTP requests to external APIs with authentication support
"""
import httpx
from typing import Dict, Any, Optional
from .base import BaseTool, ToolOutput


class APIIntegrationTool(BaseTool):
    """Tool for making HTTP API requests with authentication"""

    def __init__(
        self,
        name: str = "api_integration",
        description: str = "Make HTTP API requests (GET, POST) with authentication support",
        endpoint: Optional[str] = None,
        method: str = "GET",
        auth_type: str = "none",
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ):
        super().__init__(name, description)
        self.endpoint = endpoint
        self.method = method.upper()
        self.auth_type = auth_type
        self.headers = headers or {}
        self.timeout = timeout

    async def execute(self, input_data: Dict[str, Any]) -> ToolOutput:
        """
        Execute an API request

        Args:
            input_data: Dictionary containing:
                - url: API endpoint URL (optional if set in init)
                - method: HTTP method (optional if set in init)
                - token: Authentication token (optional)
                - headers: Additional headers (optional)
                - params: Query parameters for GET (optional)
                - body: Request body for POST (optional)
                - timeout: Request timeout in seconds (optional)

        Returns:
            ToolOutput with API response data
        """
        try:
            # Get parameters from input or use defaults
            url = input_data.get("url", self.endpoint)
            if not url:
                return ToolOutput(
                    success=False,
                    result=None,
                    error="URL is required"
                )

            method = input_data.get("method", self.method).upper()
            if method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                return ToolOutput(
                    success=False,
                    result=None,
                    error=f"Unsupported HTTP method: {method}"
                )

            # Build headers
            headers = self.headers.copy()

            # Add custom headers from input
            if "headers" in input_data:
                headers.update(input_data["headers"])

            # Add authentication token if provided
            token = input_data.get("token")
            auth_type = input_data.get("auth_type", self.auth_type)

            if token:
                if auth_type == "bearer":
                    headers["Authorization"] = f"Bearer {token}"
                elif auth_type == "api_key":
                    # Can be customized based on API requirements
                    headers["X-API-Key"] = token
                elif auth_type == "basic":
                    # For basic auth, token should be base64 encoded "username:password"
                    headers["Authorization"] = f"Basic {token}"

            # Get timeout
            timeout = input_data.get("timeout", self.timeout)

            # Make the HTTP request
            async with httpx.AsyncClient(timeout=timeout) as client:
                if method == "GET":
                    params = input_data.get("params", {})
                    response = await client.get(url, headers=headers, params=params)

                elif method == "POST":
                    body = input_data.get("body", {})
                    # Automatically set Content-Type if not provided
                    if "Content-Type" not in headers:
                        headers["Content-Type"] = "application/json"
                    response = await client.post(url, headers=headers, json=body)

                elif method == "PUT":
                    body = input_data.get("body", {})
                    if "Content-Type" not in headers:
                        headers["Content-Type"] = "application/json"
                    response = await client.put(url, headers=headers, json=body)

                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)

                elif method == "PATCH":
                    body = input_data.get("body", {})
                    if "Content-Type" not in headers:
                        headers["Content-Type"] = "application/json"
                    response = await client.patch(url, headers=headers, json=body)

            # Parse response
            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "url": str(response.url)
            }

            # Try to parse JSON response
            try:
                result["data"] = response.json()
            except Exception:
                result["data"] = response.text

            # Check if request was successful
            if response.is_success:
                return ToolOutput(
                    success=True,
                    result=result,
                    error=None
                )
            else:
                return ToolOutput(
                    success=False,
                    result=result,
                    error=f"HTTP {response.status_code}: {response.reason_phrase}"
                )

        except httpx.TimeoutException:
            return ToolOutput(
                success=False,
                result=None,
                error=f"Request timed out after {timeout} seconds"
            )

        except httpx.RequestError as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"Request error: {str(e)}"
            )

        except Exception as e:
            return ToolOutput(
                success=False,
                result=None,
                error=f"Unexpected error: {str(e)}"
            )

    def _get_parameters(self) -> Dict[str, Any]:
        """Define the parameters schema for this tool"""
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "API endpoint URL"
                },
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                    "description": "HTTP method",
                    "default": "GET"
                },
                "token": {
                    "type": "string",
                    "description": "Authentication token"
                },
                "auth_type": {
                    "type": "string",
                    "enum": ["none", "bearer", "api_key", "basic"],
                    "description": "Authentication type",
                    "default": "bearer"
                },
                "headers": {
                    "type": "object",
                    "description": "Additional HTTP headers",
                    "additionalProperties": {"type": "string"}
                },
                "params": {
                    "type": "object",
                    "description": "Query parameters (for GET requests)",
                    "additionalProperties": {"type": "string"}
                },
                "body": {
                    "type": "object",
                    "description": "Request body (for POST/PUT/PATCH requests)"
                },
                "timeout": {
                    "type": "integer",
                    "description": "Request timeout in seconds",
                    "default": 30
                }
            },
            "required": ["url"]
        }
