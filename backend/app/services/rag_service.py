"""
RAG Retrieval Service using pgvector
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.models.vector_store import Collection, Document, DocumentChunk
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings


class RAGService:
    """Service for retrieving relevant documents using pgvector."""

    def __init__(
        self,
        db: AsyncSession,
        embedding_provider: str = "openai",
        embedding_model: str = "text-embedding-ada-002",
        api_key: Optional[str] = None
    ):
        """
        Initialize RAG service.

        Args:
            db: Database session (pgvector database)
            embedding_provider: Embedding provider (openai, anthropic, google)
            embedding_model: Embedding model name
            api_key: Optional API key for the embedding provider
        """
        self.db = db
        self.embedding_provider = embedding_provider
        self.embedding_model = embedding_model
        self.api_key = api_key
        self.embeddings = self._get_embeddings_client()

    def _get_embeddings_client(self):
        """Create embeddings client based on provider."""
        if self.embedding_provider == "openai":
            params = {"model": self.embedding_model}
            if self.api_key:
                params["api_key"] = self.api_key
            return OpenAIEmbeddings(**params)
        elif self.embedding_provider == "google":
            params = {"model": self.embedding_model}
            if self.api_key:
                params["google_api_key"] = self.api_key
            return GoogleGenerativeAIEmbeddings(**params)
        elif self.embedding_provider == "voyage":
            # Voyage AI is recommended by Anthropic for embeddings
            from langchain_community.embeddings import VoyageEmbeddings
            params = {"model": self.embedding_model}
            if self.api_key:
                params["voyage_api_key"] = self.api_key
            return VoyageEmbeddings(**params)
        else:
            raise ValueError(f"Unsupported embedding provider: {self.embedding_provider}. Supported: openai, google, voyage")

    async def retrieve_relevant_chunks(
        self,
        query: str,
        collection_id: Optional[int] = None,
        top_k: int = 5,
        score_threshold: float = 0.7,
        search_method: str = "cosine"
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant document chunks using vector similarity.

        Args:
            query: User query text
            collection_id: Optional collection to filter by
            top_k: Number of chunks to retrieve
            score_threshold: Minimum similarity score (0-1)
            search_method: 'cosine' or 'l2' distance

        Returns:
            List of chunks with metadata and scores
        """
        # Generate query embedding
        query_embedding = await self.embeddings.aembed_query(query)

        # Choose distance operator
        distance_op = "<->" if search_method == "cosine" else "<=>"

        # Build similarity search query
        query_sql = f"""
        SELECT
            dc.id,
            dc.chunk_text,
            dc.chunk_index,
            dc.provider,
            dc.model,
            d.filename,
            d.file_type,
            d.metadata as doc_metadata,
            c.name as collection_name,
            1 - (dc.embedding {distance_op} :embedding::vector) as similarity_score
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        JOIN collections c ON d.collection_id = c.id
        WHERE 1 - (dc.embedding {distance_op} :embedding::vector) >= :threshold
        """

        # Add collection filter if specified
        params = {
            "embedding": query_embedding,
            "threshold": score_threshold,
            "limit": top_k
        }

        if collection_id:
            query_sql += " AND d.collection_id = :collection_id"
            params["collection_id"] = collection_id

        query_sql += f"""
        ORDER BY dc.embedding {distance_op} :embedding::vector
        LIMIT :limit
        """

        # Execute query
        result = await self.db.execute(text(query_sql), params)
        rows = result.fetchall()

        # Format results
        chunks = []
        for row in rows:
            chunks.append({
                "chunk_id": row[0],
                "text": row[1],
                "chunk_index": row[2],
                "provider": row[3],
                "model": row[4],
                "filename": row[5],
                "file_type": row[6],
                "metadata": row[7],
                "collection": row[8],
                "score": float(row[9])
            })

        return chunks

    async def get_collections(
        self,
        user_id: Optional[int] = None,
        include_public: bool = True
    ) -> List[Collection]:
        """
        Get available collections for a user.

        Args:
            user_id: Optional user ID to filter by
            include_public: Include public collections

        Returns:
            List of Collection objects
        """
        query = select(Collection)

        if user_id:
            if include_public:
                query = query.where(
                    (Collection.created_by == user_id) |
                    (Collection.is_public == True)
                )
            else:
                query = query.where(Collection.created_by == user_id)
        elif include_public:
            query = query.where(Collection.is_public == True)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_collection_by_id(self, collection_id: int) -> Optional[Collection]:
        """
        Get a collection by ID.

        Args:
            collection_id: Collection ID

        Returns:
            Collection object or None
        """
        result = await self.db.execute(
            select(Collection).where(Collection.id == collection_id)
        )
        return result.scalar_one_or_none()

    async def format_rag_context(
        self,
        chunks: List[Dict[str, Any]],
        include_metadata: bool = True
    ) -> str:
        """
        Format retrieved chunks into context for LLM.

        Args:
            chunks: Retrieved chunks from retrieve_relevant_chunks
            include_metadata: Include source metadata in context

        Returns:
            Formatted context string
        """
        if not chunks:
            return ""

        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            if include_metadata:
                header = f"[Document {i}: {chunk['filename']} (Score: {chunk['score']:.3f})]"
                context_parts.append(f"{header}\n{chunk['text']}")
            else:
                context_parts.append(chunk['text'])

        return "\n\n".join(context_parts)

    @staticmethod
    def create_from_collection(
        db: AsyncSession,
        collection: Collection,
        api_key: Optional[str] = None
    ) -> "RAGService":
        """
        Create RAG service from a collection's embedding configuration.

        Args:
            db: Database session (pgvector database)
            collection: Collection with embedding config
            api_key: Optional API key for the embedding provider

        Returns:
            RAGService instance
        """
        return RAGService(
            db=db,
            embedding_provider=collection.embedding_provider or "openai",
            embedding_model=collection.embedding_model or "text-embedding-ada-002",
            api_key=api_key
        )
