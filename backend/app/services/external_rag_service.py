"""
External RAG Service for DemystRAG Integration
"""
import httpx
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ExternalRAGService:
    """Service for retrieving documents from external DemystRAG API."""

    def __init__(
        self,
        base_url: str = "http://localhost:8003",
        api_key: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        Initialize External RAG service.

        Args:
            base_url: DemystRAG API base URL
            api_key: API key for authentication (dmr_xxx format)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    async def search(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        collection_id: Optional[int] = None,
        document_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Search for relevant chunks using DemystRAG API.

        Args:
            query: Search query text
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score (0-1)
            collection_id: Optional collection filter
            document_ids: Optional document IDs filter

        Returns:
            Search response with chunks
        """
        payload = {
            "query": query,
            "top_k": top_k,
            "similarity_threshold": similarity_threshold
        }

        if collection_id:
            payload["collection_id"] = collection_id
        if document_ids:
            payload["document_ids"] = document_ids

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/v1/search",
                    headers=self._get_headers(),
                    json=payload
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"DemystRAG search failed: {e.response.status_code} - {e.response.text}")
                raise ValueError(f"RAG search failed: {e.response.text}")
            except httpx.RequestError as e:
                logger.error(f"DemystRAG connection failed: {str(e)}")
                raise ValueError(f"Failed to connect to RAG service: {str(e)}")

    async def retrieve_relevant_chunks(
        self,
        query: str,
        collection_id: Optional[int] = None,
        top_k: int = 5,
        score_threshold: float = 0.7,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant document chunks (compatible interface with RAGService).

        Args:
            query: User query text
            collection_id: Optional collection to filter by
            top_k: Number of chunks to retrieve
            score_threshold: Minimum similarity score (0-1)

        Returns:
            List of chunks with metadata and scores
        """
        result = await self.search(
            query=query,
            top_k=top_k,
            similarity_threshold=score_threshold,
            collection_id=collection_id
        )

        # Transform DemystRAG response to match internal format
        chunks = []
        for chunk in result.get("chunks", []):
            chunks.append({
                "chunk_id": chunk.get("id"),
                "text": chunk.get("text", ""),
                "chunk_index": chunk.get("chunk_index", 0),
                "provider": chunk.get("provider", "external"),
                "model": chunk.get("model", "unknown"),
                "filename": f"doc_{chunk.get('document_id', 'unknown')}",
                "file_type": "external",
                "metadata": {},
                "collection": f"collection_{collection_id}" if collection_id else "default",
                "score": chunk.get("similarity", 0.0)
            })

        return chunks

    async def list_collections(self) -> List[Dict[str, Any]]:
        """
        List all available collections.

        Returns:
            List of collections
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v1/collections",
                    headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()
                return data.get("collections", [])
            except httpx.HTTPStatusError as e:
                logger.error(f"DemystRAG list collections failed: {e.response.status_code}")
                raise ValueError(f"Failed to list collections: {e.response.text}")
            except httpx.RequestError as e:
                logger.error(f"DemystRAG connection failed: {str(e)}")
                raise ValueError(f"Failed to connect to RAG service: {str(e)}")

    async def get_collection(self, collection_id: int) -> Dict[str, Any]:
        """
        Get collection details.

        Args:
            collection_id: Collection ID

        Returns:
            Collection details
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v1/collections/{collection_id}",
                    headers=self._get_headers()
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"DemystRAG get collection failed: {e.response.status_code}")
                raise ValueError(f"Failed to get collection: {e.response.text}")
            except httpx.RequestError as e:
                logger.error(f"DemystRAG connection failed: {str(e)}")
                raise ValueError(f"Failed to connect to RAG service: {str(e)}")

    async def list_documents(
        self,
        collection_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List documents, optionally filtered by collection.

        Args:
            collection_id: Optional collection filter

        Returns:
            List of documents
        """
        params = {}
        if collection_id:
            params["collection_id"] = collection_id

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/v1/documents",
                    headers=self._get_headers(),
                    params=params
                )
                response.raise_for_status()
                data = response.json()
                return data.get("documents", [])
            except httpx.HTTPStatusError as e:
                logger.error(f"DemystRAG list documents failed: {e.response.status_code}")
                raise ValueError(f"Failed to list documents: {e.response.text}")
            except httpx.RequestError as e:
                logger.error(f"DemystRAG connection failed: {str(e)}")
                raise ValueError(f"Failed to connect to RAG service: {str(e)}")

    async def format_rag_context(
        self,
        chunks: List[Dict[str, Any]],
        include_metadata: bool = True
    ) -> str:
        """
        Format retrieved chunks into context for LLM.

        Args:
            chunks: Retrieved chunks
            include_metadata: Include source metadata in context

        Returns:
            Formatted context string
        """
        if not chunks:
            return ""

        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            if include_metadata:
                header = f"[Document {i}: {chunk.get('filename', 'unknown')} (Score: {chunk.get('score', 0):.3f})]"
                context_parts.append(f"{header}\n{chunk.get('text', '')}")
            else:
                context_parts.append(chunk.get('text', ''))

        return "\n\n".join(context_parts)

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to DemystRAG API.

        Returns:
            Connection test result with status and details
        """
        try:
            collections = await self.list_collections()
            return {
                "success": True,
                "message": f"Connected successfully. Found {len(collections)} collections.",
                "collection_count": len(collections)
            }
        except Exception as e:
            logger.error(f"DemystRAG connection test failed: {str(e)}")
            return {
                "success": False,
                "message": str(e),
                "collection_count": 0
            }
