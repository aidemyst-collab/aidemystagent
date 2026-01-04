"""
RAG API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from pydantic import BaseModel
from uuid import UUID

from app.core.database import get_db, get_pgvector_db
from app.services.rag_service import RAGService
from app.services.external_rag_service import ExternalRAGService
from app.models.vector_store import Collection
from app.models.user import User
from app.models.credential import Credential
from app.api.deps import get_current_active_user, require_permission


router = APIRouter()


class CollectionResponse(BaseModel):
    """Collection response schema."""
    id: int
    name: str
    description: Optional[str]
    created_by: Optional[int]
    created_at: Optional[str]
    is_public: bool
    embedding_provider: Optional[str]
    embedding_model: Optional[str]


class RAGTestRequest(BaseModel):
    """RAG test request schema."""
    query: str
    collection_id: Optional[int] = None
    credential_id: Optional[UUID] = None  # Credential for embedding provider
    top_k: int = 5
    score_threshold: float = 0.7
    search_method: str = "cosine"
    embedding_provider: Optional[str] = None
    embedding_model: Optional[str] = None
    include_metadata: bool = True


class ChunkResult(BaseModel):
    """Retrieved chunk result."""
    chunk_id: int
    text: str
    chunk_index: Optional[int]
    provider: Optional[str]
    model: Optional[str]
    filename: str
    file_type: Optional[str]
    collection: str
    score: float


class RAGTestResponse(BaseModel):
    """RAG test response schema."""
    success: bool
    chunks: List[ChunkResult]
    context: str
    total_retrieved: int
    query_used: str


@router.get("/collections")
async def get_collections(
    pgvector_db: AsyncSession = Depends(get_pgvector_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("rag:read")),
):
    """Get available collections for the user."""
    try:
        rag_service = RAGService(pgvector_db)
        collections = await rag_service.get_collections(
            user_id=current_user.id if hasattr(current_user, 'id') else None,
            include_public=True
        )

        return {
            "collections": [
                {
                    "id": c.id,
                    "name": c.name,
                    "description": c.description,
                    "created_by": c.created_by,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "is_public": c.is_public,
                    "embedding_provider": c.embedding_provider,
                    "embedding_model": c.embedding_model,
                }
                for c in collections
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching collections: {str(e)}"
        )


@router.get("/collections/{collection_id}")
async def get_collection(
    collection_id: int,
    pgvector_db: AsyncSession = Depends(get_pgvector_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("rag:read")),
):
    """Get a specific collection by ID."""
    try:
        rag_service = RAGService(pgvector_db)
        collection = await rag_service.get_collection_by_id(collection_id)

        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection not found"
            )

        return {
            "id": collection.id,
            "name": collection.name,
            "description": collection.description,
            "created_by": collection.created_by,
            "created_at": collection.created_at.isoformat() if collection.created_at else None,
            "is_public": collection.is_public,
            "embedding_provider": collection.embedding_provider,
            "embedding_model": collection.embedding_model,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching collection: {str(e)}"
        )


@router.post("/test")
async def test_retrieval(
    request: RAGTestRequest,
    main_db: AsyncSession = Depends(get_db),
    pgvector_db: AsyncSession = Depends(get_pgvector_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_permission("rag:execute")),
):
    """Test RAG retrieval with a query."""
    try:
        # Get API key from credentials if provided
        api_key = None
        if request.credential_id:
            result = await main_db.execute(
                select(Credential).where(Credential.id == request.credential_id)
            )
            credential = result.scalar_one_or_none()
            if not credential:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Credential not found"
                )
            api_key = credential.api_key

        # If collection specified, get its embedding config
        embedding_provider = request.embedding_provider
        embedding_model = request.embedding_model

        if request.collection_id and not (embedding_provider and embedding_model):
            rag_service_temp = RAGService(pgvector_db)
            collection = await rag_service_temp.get_collection_by_id(request.collection_id)
            if collection:
                embedding_provider = collection.embedding_provider or "openai"
                embedding_model = collection.embedding_model or "text-embedding-ada-002"
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Collection not found"
                )
        else:
            embedding_provider = embedding_provider or "openai"
            embedding_model = embedding_model or "text-embedding-ada-002"

        # Create RAG service with appropriate embedding config and API key
        rag_service = RAGService(
            pgvector_db,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
            api_key=api_key
        )

        # Retrieve chunks
        chunks = await rag_service.retrieve_relevant_chunks(
            query=request.query,
            collection_id=request.collection_id,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            search_method=request.search_method
        )

        # Format context
        context = await rag_service.format_rag_context(
            chunks,
            include_metadata=request.include_metadata
        )

        return {
            "success": True,
            "chunks": chunks,
            "context": context,
            "total_retrieved": len(chunks),
            "query_used": request.query
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during retrieval: {str(e)}"
        )


# =============================================================================
# External RAG (DemystRAG) Endpoints
# =============================================================================

class ExternalRAGConnectionRequest(BaseModel):
    """External RAG connection test request."""
    url: str
    api_key: str


class ExternalRAGSearchRequest(BaseModel):
    """External RAG search request."""
    url: str
    api_key: str
    query: str
    collection_id: Optional[int] = None
    top_k: int = 5
    similarity_threshold: float = 0.7


@router.post("/external/test")
async def test_external_connection(
    request: ExternalRAGConnectionRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Test connection to external DemystRAG system."""
    try:
        service = ExternalRAGService(
            base_url=request.url,
            api_key=request.api_key
        )
        result = await service.test_connection()
        return result
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "collection_count": 0
        }


@router.post("/external/collections")
async def get_external_collections(
    request: ExternalRAGConnectionRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Fetch collections from external DemystRAG system."""
    try:
        service = ExternalRAGService(
            base_url=request.url,
            api_key=request.api_key
        )
        collections = await service.list_collections()
        return {
            "success": True,
            "collections": collections
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/external/search")
async def search_external_rag(
    request: ExternalRAGSearchRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Search external DemystRAG system."""
    try:
        service = ExternalRAGService(
            base_url=request.url,
            api_key=request.api_key
        )
        chunks = await service.retrieve_relevant_chunks(
            query=request.query,
            collection_id=request.collection_id,
            top_k=request.top_k,
            score_threshold=request.similarity_threshold
        )
        context = await service.format_rag_context(chunks)
        return {
            "success": True,
            "chunks": chunks,
            "context": context,
            "total_retrieved": len(chunks)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
