from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import httpx
from pydantic import BaseModel


class RAGDocument(BaseModel):
    """Represents a document from RAG retrieval."""
    content: str
    metadata: Dict[str, Any]
    score: float


class RAGConnector(ABC):
    """Abstract base class for RAG connectors."""

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.7
    ) -> List[RAGDocument]:
        """Retrieve documents from RAG system."""
        pass

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to RAG system."""
        pass


class RESTRAGConnector(RAGConnector):
    """RAG connector for REST APIs."""

    def __init__(
        self,
        endpoint: str,
        auth_type: str = "api_key",
        auth_credentials: Dict[str, str] = None,
        search_method: str = "semantic",
    ):
        self.endpoint = endpoint
        self.auth_type = auth_type
        self.auth_credentials = auth_credentials or {}
        self.search_method = search_method

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.7
    ) -> List[RAGDocument]:
        """Retrieve documents from REST RAG system."""
        try:
            headers = self._get_auth_headers()

            payload = {
                "query": query,
                "top_k": top_k,
                "score_threshold": score_threshold,
                "search_method": self.search_method,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.endpoint}/search",
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                response.raise_for_status()

                data = response.json()
                documents = data.get("documents", [])

                return [
                    RAGDocument(
                        content=doc.get("content", ""),
                        metadata=doc.get("metadata", {}),
                        score=doc.get("score", 0.0)
                    )
                    for doc in documents
                ]

        except Exception as e:
            # Log error and return empty results
            print(f"RAG retrieval error: {e}")
            return []

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to RAG system."""
        try:
            headers = self._get_auth_headers()

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.endpoint}/health",
                    headers=headers,
                    timeout=10.0
                )
                response.raise_for_status()

                return {
                    "success": True,
                    "message": "Connection successful",
                    "endpoint": self.endpoint,
                }

        except Exception as e:
            return {
                "success": False,
                "message": str(e),
                "endpoint": self.endpoint,
            }

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers based on auth type."""
        headers = {"Content-Type": "application/json"}

        if self.auth_type == "api_key":
            api_key = self.auth_credentials.get("api_key", "")
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

        elif self.auth_type == "basic":
            username = self.auth_credentials.get("username", "")
            password = self.auth_credentials.get("password", "")
            if username and password:
                import base64
                credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                headers["Authorization"] = f"Basic {credentials}"

        return headers


class GraphQLRAGConnector(RAGConnector):
    """RAG connector for GraphQL APIs."""

    def __init__(
        self,
        endpoint: str,
        auth_type: str = "api_key",
        auth_credentials: Dict[str, str] = None,
    ):
        self.endpoint = endpoint
        self.auth_type = auth_type
        self.auth_credentials = auth_credentials or {}

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.7
    ) -> List[RAGDocument]:
        """Retrieve documents from GraphQL RAG system."""
        try:
            headers = self._get_auth_headers()

            graphql_query = """
            query Search($query: String!, $topK: Int!, $threshold: Float!) {
                search(query: $query, topK: $topK, threshold: $threshold) {
                    content
                    metadata
                    score
                }
            }
            """

            variables = {
                "query": query,
                "topK": top_k,
                "threshold": score_threshold,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.endpoint,
                    json={"query": graphql_query, "variables": variables},
                    headers=headers,
                    timeout=30.0
                )
                response.raise_for_status()

                data = response.json()
                documents = data.get("data", {}).get("search", [])

                return [
                    RAGDocument(
                        content=doc.get("content", ""),
                        metadata=doc.get("metadata", {}),
                        score=doc.get("score", 0.0)
                    )
                    for doc in documents
                ]

        except Exception as e:
            print(f"RAG retrieval error: {e}")
            return []

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to GraphQL RAG system."""
        try:
            headers = self._get_auth_headers()

            health_query = "{ health { status } }"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.endpoint,
                    json={"query": health_query},
                    headers=headers,
                    timeout=10.0
                )
                response.raise_for_status()

                return {
                    "success": True,
                    "message": "Connection successful",
                    "endpoint": self.endpoint,
                }

        except Exception as e:
            return {
                "success": False,
                "message": str(e),
                "endpoint": self.endpoint,
            }

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        headers = {"Content-Type": "application/json"}

        if self.auth_type == "api_key":
            api_key = self.auth_credentials.get("api_key", "")
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

        return headers


def create_rag_connector(config: Dict[str, Any]) -> RAGConnector:
    """Factory function to create RAG connector from configuration."""
    connector_type = config.get("type", "rest")
    endpoint = config.get("endpoint", "")
    auth_type = config.get("auth_type", "api_key")
    auth_credentials = config.get("auth_credentials", {})

    if connector_type == "rest":
        return RESTRAGConnector(
            endpoint=endpoint,
            auth_type=auth_type,
            auth_credentials=auth_credentials,
            search_method=config.get("search_method", "semantic"),
        )
    elif connector_type == "graphql":
        return GraphQLRAGConnector(
            endpoint=endpoint,
            auth_type=auth_type,
            auth_credentials=auth_credentials,
        )
    else:
        raise ValueError(f"Unknown RAG connector type: {connector_type}")
