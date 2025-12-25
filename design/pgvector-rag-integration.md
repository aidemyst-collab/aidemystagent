# pgvector RAG Integration Implementation

## Overview
Integration of existing pgvector database with the RAG Retriever node in the hub-and-spoke LLM agent architecture.

## Database Structure

### Connection Details
```
Database: demystrag
Host: localhost:5433
User: demystrag_user
URL: postgresql://demystrag_user:demystrag_password@localhost:5433/demystrag
pgvector version: 0.8.1
```

### Existing Tables

#### 1. collections
Organizes documents into collections (by project, user, topic, etc.)
```sql
CREATE TABLE collections (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    created_by INTEGER,
    created_at TIMESTAMP,
    is_public BOOLEAN,
    embedding_provider VARCHAR,  -- e.g., 'openai', 'cohere'
    embedding_model VARCHAR       -- e.g., 'text-embedding-ada-002'
);
```

#### 2. documents
Stores uploaded files and their metadata
```sql
CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    filename VARCHAR NOT NULL,
    file_type VARCHAR,           -- pdf, txt, docx, etc.
    content TEXT,                -- Full document text
    uploaded_at TIMESTAMP,
    metadata TEXT,               -- JSON metadata
    collection_id INTEGER REFERENCES collections(id)
);
```

#### 3. document_chunks
Stores text chunks with vector embeddings (main table for RAG)
```sql
CREATE TABLE document_chunks (
    id INTEGER PRIMARY KEY,
    document_id INTEGER REFERENCES documents(id),
    chunk_text TEXT NOT NULL,           -- The actual text chunk
    chunk_index INTEGER,                -- Position in document
    embedding VECTOR(1536) NOT NULL,    -- Vector embedding
    provider VARCHAR,                   -- Embedding provider used
    model VARCHAR,                      -- Embedding model used
    created_at TIMESTAMP
);

-- Indexes
CREATE INDEX ix_document_chunks_document_id ON document_chunks(document_id);
```

#### 4. users
User management for the pgvector application
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username VARCHAR NOT NULL,
    email VARCHAR NOT NULL,
    hashed_password VARCHAR,
    role VARCHAR,
    is_active BOOLEAN,
    created_at TIMESTAMP,
    created_by INTEGER
);
```

### Current Statistics
- Total collections: 1
- Total documents: 0
- Total chunks: 0
- Embedding dimension: 1536 (OpenAI text-embedding-ada-002 or text-embedding-3-small)

---

## How RAG Retrieval Works with Embeddings

### The Dual Embedding Process

RAG involves **two separate embedding operations**:

#### 1. Storage Phase (Done Once per Document)
When documents are initially stored in pgvector:

```
Document Text → Embedding Model → Vector → Store in Database
─────────────────────────────────────────────────────────────
"The price is $99/month"
    ↓
OpenAI text-embedding-ada-002
    ↓
[0.123, -0.456, 0.789, 0.234, ..., -0.156]  (1536 numbers)
    ↓
INSERT INTO document_chunks (chunk_text, embedding, model)
VALUES ('The price is $99/month', [0.123, ...], 'text-embedding-ada-002')
```

#### 2. Retrieval Phase (Every User Query)
When retrieving relevant context for a user question:

```
User Query → SAME Embedding Model → Query Vector → Similarity Search → Results
─────────────────────────────────────────────────────────────────────────────────
"What is the pricing?"
    ↓
OpenAI text-embedding-ada-002  ← MUST BE SAME MODEL!
    ↓
[0.145, -0.423, 0.812, 0.241, ..., -0.134]  (1536 numbers)
    ↓
SELECT chunk_text, 1 - (embedding <-> [0.145, ...]) as score
FROM document_chunks
WHERE 1 - (embedding <-> [0.145, ...]) >= 0.7
ORDER BY embedding <-> [0.145, ...]
LIMIT 5
    ↓
[
  {"text": "The price is $99/month", "score": 0.89},
  {"text": "Pricing plans start at $49", "score": 0.82},
  ...
]
```

### ⚠️ Critical Rule: Model Consistency

**The embedding model used for retrieval MUST match the model used for storage!**

```python
# ❌ WRONG - Mismatched models = poor results
# Storage:   text-embedding-ada-002 (1536d)
# Retrieval: text-embedding-3-large (3072d)
# Result:    Incompatible vector spaces, meaningless similarity scores

# ✅ CORRECT - Same model = accurate similarity
# Storage:   text-embedding-ada-002 (1536d)
# Retrieval: text-embedding-ada-002 (1536d)
# Result:    Accurate semantic similarity matching
```

### Why Model Tracking is Critical

This is why the `collections` table stores `embedding_provider` and `embedding_model`:

```python
# When creating a collection, record which model was used
collection = Collection(
    name="Product Documentation",
    embedding_provider="openai",
    embedding_model="text-embedding-ada-002"
)

# When retrieving, use the SAME model
rag_service = RAGService(
    db=db,
    embedding_provider=collection.embedding_provider,  # ← From DB
    embedding_model=collection.embedding_model          # ← From DB
)
```

### Complete Retrieval Flow

```python
# User asks: "What is the pricing?"
query = "What is the pricing?"

# STEP 1: Get collection configuration
collection = await db.get(Collection, collection_id)
# collection.embedding_model = "text-embedding-ada-002"

# STEP 2: Initialize embeddings client with SAME model
embeddings = OpenAIEmbeddings(model=collection.embedding_model)

# STEP 3: Embed the user's query
query_embedding = await embeddings.aembed_query(query)
# query_embedding = [0.145, -0.423, 0.812, ...]  (1536 floats)

# STEP 4: Perform vector similarity search
results = await db.execute("""
    SELECT
        chunk_text,
        filename,
        1 - (embedding <-> :query_vec) as similarity_score
    FROM document_chunks dc
    JOIN documents d ON dc.document_id = d.id
    WHERE 1 - (embedding <-> :query_vec) >= 0.7
    ORDER BY embedding <-> :query_vec
    LIMIT 5
""", {"query_vec": query_embedding})

# STEP 5: Format results for LLM
chunks = [
    {"text": "The price is $99/month", "score": 0.89},
    {"text": "Pricing plans start at $49", "score": 0.82},
    ...
]

context = """
[Document 1: pricing.pdf (Score: 0.89)]
The price is $99/month

[Document 2: plans.pdf (Score: 0.82)]
Pricing plans start at $49
"""

# STEP 6: Inject context into LLM prompt
messages = [
    SystemMessage(content=f"Use this context:\n{context}"),
    HumanMessage(content=query)
]
```

### Vector Similarity Operators

pgvector provides different distance operators:

| Operator | Distance Type | SQL Example | Use Case |
|----------|---------------|-------------|----------|
| `<->` | Cosine distance | `embedding <-> query` | Most common, normalized vectors |
| `<#>` | Negative inner product | `embedding <#> query` | When vectors are normalized |
| `<=>` | L2 distance (Euclidean) | `embedding <=> query` | Absolute distance matters |

**Most RAG systems use cosine distance (`<->`)**:
```sql
-- Cosine similarity = 1 - cosine distance
SELECT 1 - (embedding <-> :query_embedding) as similarity_score
```

### Embedding Model Options

**OpenAI** (most common):
- `text-embedding-ada-002`: 1536d, $0.0001/1K tokens, legacy but reliable
- `text-embedding-3-small`: 1536d, $0.00002/1K tokens, better performance
- `text-embedding-3-large`: 3072d, $0.00013/1K tokens, highest quality

**Anthropic**:
- `voyage-2`: 1024d, optimized for Claude

**Google**:
- `text-embedding-004`: 768d, multilingual support

**Important**: Once you choose a model and store embeddings, you're committed to that model for that collection unless you re-embed all documents.

### Credentials Required

The RAG service needs API credentials to generate query embeddings:

```python
# For OpenAI
import os
os.environ["OPENAI_API_KEY"] = "sk-..."

# For Anthropic
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."

# For Google
os.environ["GOOGLE_API_KEY"] = "..."
```

These are typically stored in the credentials table and fetched based on the collection's `embedding_provider`.

---

## Implementation Plan

### Phase 1: Database Optimization

#### 1.1 Create Vector Similarity Index
Add HNSW index for fast similarity search on document_chunks:

```sql
-- HNSW index (recommended for most use cases)
CREATE INDEX document_chunks_embedding_idx
ON document_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Alternative: IVFFlat index (for very large datasets)
-- CREATE INDEX document_chunks_embedding_idx
-- ON document_chunks
-- USING ivfflat (embedding vector_cosine_ops)
-- WITH (lists = 100);
```

**Index Parameters:**
- `m = 16`: Max connections per layer (higher = better recall, slower build)
- `ef_construction = 64`: Size of dynamic candidate list (higher = better quality)
- `vector_cosine_ops`: Cosine similarity (can also use L2 distance with `vector_l2_ops`)

#### 1.2 Add Collection Metadata Index
```sql
CREATE INDEX ix_collections_created_by ON collections(created_by);
CREATE INDEX ix_documents_collection_id ON documents(collection_id);
```

### Phase 2: Backend Implementation

#### 2.1 Create SQLAlchemy Models
**File:** `backend/app/models/vector_store.py`

```python
"""
pgvector models for RAG retrieval
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from datetime import datetime
from app.core.database import Base


class Collection(Base):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_public = Column(Boolean, default=False)
    embedding_provider = Column(String)  # openai, cohere, etc.
    embedding_model = Column(String)     # text-embedding-ada-002, etc.

    # Relationships
    documents = relationship("Document", back_populates="collection")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    file_type = Column(String)
    content = Column(Text)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    metadata = Column(Text)  # JSON string
    collection_id = Column(Integer, ForeignKey("collections.id"), index=True)

    # Relationships
    collection = relationship("Collection", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), index=True)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer)
    embedding = Column(Vector(1536), nullable=False)
    provider = Column(String)
    model = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="chunks")
```

#### 2.2 Create RAG Retrieval Service
**File:** `backend/app/services/rag_service.py`

```python
"""
RAG Retrieval Service using pgvector
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from app.models.vector_store import Collection, Document, DocumentChunk
from langchain_openai import OpenAIEmbeddings
from langchain_anthropic import AnthropicEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings


class RAGService:
    """Service for retrieving relevant documents using pgvector."""

    def __init__(
        self,
        db: AsyncSession,
        embedding_provider: str = "openai",
        embedding_model: str = "text-embedding-ada-002"
    ):
        self.db = db
        self.embedding_provider = embedding_provider
        self.embedding_model = embedding_model
        self.embeddings = self._get_embeddings_client()

    def _get_embeddings_client(self):
        """Create embeddings client based on provider."""
        if self.embedding_provider == "openai":
            return OpenAIEmbeddings(model=self.embedding_model)
        elif self.embedding_provider == "anthropic":
            return AnthropicEmbeddings(model=self.embedding_model)
        elif self.embedding_provider == "google":
            return GoogleGenerativeAIEmbeddings(model=self.embedding_model)
        else:
            raise ValueError(f"Unsupported embedding provider: {self.embedding_provider}")

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

        # Build similarity search query
        distance_op = "<->" if search_method == "cosine" else "<->"

        # Base query
        query_sql = f"""
        SELECT
            dc.id,
            dc.chunk_text,
            dc.chunk_index,
            dc.provider,
            dc.model,
            d.filename,
            d.file_type,
            c.name as collection_name,
            1 - (dc.embedding {distance_op} :embedding) as similarity_score
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        JOIN collections c ON d.collection_id = c.id
        WHERE 1 - (dc.embedding {distance_op} :embedding) >= :threshold
        """

        # Add collection filter if specified
        if collection_id:
            query_sql += " AND d.collection_id = :collection_id"

        query_sql += """
        ORDER BY dc.embedding {distance_op} :embedding
        LIMIT :limit
        """

        # Execute query
        params = {
            "embedding": query_embedding,
            "threshold": score_threshold,
            "limit": top_k
        }

        if collection_id:
            params["collection_id"] = collection_id

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
                "collection": row[7],
                "score": float(row[8])
            })

        return chunks

    async def get_collections(
        self,
        user_id: Optional[int] = None,
        include_public: bool = True
    ) -> List[Collection]:
        """Get available collections for a user."""
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
```

#### 2.3 Update LLM Agent Handler
**File:** `backend/app/services/langgraph_engine.py`

Update the `_handle_llm_agent_node` method to use RAG service:

```python
from app.services.rag_service import RAGService
from app.models.vector_store import Collection

async def _handle_llm_agent_node(self, state: AgentState) -> AgentState:
    """Handle LLM_AGENT node (Hub-and-Spoke pattern)."""

    # ... existing code for memory and tools ...

    # Query RAG node if connected
    rag_context = None
    if connected["rag"] and self.db:
        rag_config = connected["rag"].get("data", {}).get("config", {})

        try:
            # Get current user query
            current_query = state["messages"][-1].content if state["messages"] else ""

            # Initialize RAG service
            rag_service = RAGService(
                db=self.db,
                embedding_provider=rag_config.get("embeddingProvider", "openai"),
                embedding_model=rag_config.get("embeddingModel", "text-embedding-ada-002")
            )

            # Retrieve relevant chunks
            chunks = await rag_service.retrieve_relevant_chunks(
                query=current_query,
                collection_id=rag_config.get("collectionId"),
                top_k=rag_config.get("topK", 5),
                score_threshold=rag_config.get("scoreThreshold", 0.7),
                search_method=rag_config.get("searchMethod", "cosine")
            )

            # Format context for LLM
            if chunks:
                rag_context = await rag_service.format_rag_context(
                    chunks,
                    include_metadata=rag_config.get("includeMetadata", True)
                )

                print(f"RAG retrieved {len(chunks)} chunks with avg score: {sum(c['score'] for c in chunks) / len(chunks):.3f}")

        except Exception as e:
            print(f"Error retrieving RAG context: {str(e)}")
            rag_context = None

    # STEP 2: Build message list for LLM
    messages = []

    # 1. Add system prompt if configured
    if system_prompt := node_config.get("systemPrompt"):
        messages.append(SystemMessage(content=system_prompt))

    # 2. Inject RAG context if available
    if rag_context:
        context_message = f"""You have access to the following relevant information from the knowledge base. Use this context to provide accurate and informed responses:

{rag_context}

Please use this context to answer the user's question. If the context doesn't contain relevant information, acknowledge this and provide your best response based on your general knowledge."""
        messages.append(SystemMessage(content=context_message))

    # 3. Add chat history if available
    if chat_history := state.get("chat_history"):
        messages.extend(chat_history)

    # 4. Add current messages
    messages.extend(state["messages"])

    # ... rest of LLM invocation code ...
```

### Phase 3: Frontend Updates

#### 3.1 Update RAG Configuration UI
**File:** `frontend/src/components/AgentBuilder/PropertyPanel.tsx`

Replace the RAG_RETRIEVER configuration section:

```typescript
{selectedNode.data.type === 'RAG_RETRIEVER' && (
  <>
    <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
      Configure pgvector retrieval for Retrieval-Augmented Generation
    </Typography.Text>

    <Card size="small" title="Collection" style={{ marginBottom: 16 }}>
      <Form.Item name={['config', 'collectionId']} label="Document Collection" rules={[{ required: true }]}>
        <Select
          placeholder="Select collection"
          showSearch
          options={collections.map(c => ({
            label: `${c.name} - ${c.description}`,
            value: c.id
          }))}
        />
      </Form.Item>

      <Form.Item name={['config', 'includeMetadata']} valuePropName="checked" initialValue={true}>
        <Checkbox>Include document metadata in context</Checkbox>
      </Form.Item>
    </Card>

    <Card size="small" title="Embedding Configuration" style={{ marginBottom: 16 }}>
      <Form.Item name={['config', 'embeddingProvider']} label="Provider" initialValue="openai">
        <Select
          options={[
            { label: 'OpenAI', value: 'openai' },
            { label: 'Anthropic', value: 'anthropic' },
            { label: 'Google', value: 'google' },
          ]}
        />
      </Form.Item>

      <Form.Item name={['config', 'embeddingModel']} label="Model" initialValue="text-embedding-ada-002">
        <Select
          options={[
            { label: 'text-embedding-ada-002 (1536d)', value: 'text-embedding-ada-002' },
            { label: 'text-embedding-3-small (1536d)', value: 'text-embedding-3-small' },
            { label: 'text-embedding-3-large (3072d)', value: 'text-embedding-3-large' },
          ]}
        />
      </Form.Item>
    </Card>

    <Card size="small" title="Retrieval Settings">
      <Form.Item name={['config', 'searchMethod']} label="Search Method" initialValue="cosine">
        <Select
          options={[
            { label: 'Cosine Similarity (recommended)', value: 'cosine' },
            { label: 'L2 Distance', value: 'l2' },
          ]}
        />
      </Form.Item>

      <Form.Item name={['config', 'topK']} label="Top K Results" initialValue={5}>
        <InputNumber
          min={1}
          max={20}
          style={{ width: '100%' }}
        />
      </Form.Item>

      <Form.Item name={['config', 'scoreThreshold']} label="Score Threshold" initialValue={0.7}>
        <InputNumber
          min={0}
          max={1}
          step={0.1}
          style={{ width: '100%' }}
        />
      </Form.Item>
    </Card>
  </>
)}
```

#### 3.2 Add Collections API Service
**File:** `frontend/src/features/rag/ragService.ts`

```typescript
import { apiClient } from '../../services/api';

export interface Collection {
  id: number;
  name: string;
  description: string;
  created_by: number;
  created_at: string;
  is_public: boolean;
  embedding_provider: string;
  embedding_model: string;
}

export const ragService = {
  /**
   * Get available collections
   */
  getCollections: async (): Promise<{ collections: Collection[] }> => {
    return apiClient.get<{ collections: Collection[] }>('/rag/collections');
  },

  /**
   * Test RAG retrieval
   */
  testRetrieval: async (
    query: string,
    collectionId: number,
    config: any
  ): Promise<any> => {
    return apiClient.post<any>('/rag/test', {
      query,
      collection_id: collectionId,
      ...config
    });
  },
};
```

#### 3.3 Update PropertyPanel to Fetch Collections
Add to PropertyPanel component:

```typescript
import { ragService, type Collection } from '../../features/rag/ragService';

// Add state
const [collections, setCollections] = useState<Collection[]>([]);

// Add fetch function
const fetchCollections = async () => {
  try {
    const data = await ragService.getCollections();
    setCollections(data.collections || []);
  } catch (error) {
    console.error('Error fetching collections:', error);
  }
};

// Update useEffect
useEffect(() => {
  fetchCredentials();
  fetchTools('built-in');
  fetchCollections(); // Add this
}, []);
```

### Phase 4: Backend API Endpoints

#### 4.1 Create RAG Router
**File:** `backend/app/api/v1/rag.py`

```python
"""
RAG API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from pydantic import BaseModel

from app.core.database import get_db
from app.services.rag_service import RAGService
from app.models.vector_store import Collection
from app.models.user import User
from app.api.deps import get_current_user


router = APIRouter()


class RAGTestRequest(BaseModel):
    query: str
    collection_id: Optional[int] = None
    top_k: int = 5
    score_threshold: float = 0.7
    search_method: str = "cosine"
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-ada-002"


@router.get("/collections")
async def get_collections(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get available collections for the user."""
    rag_service = RAGService(db)
    collections = await rag_service.get_collections(
        user_id=current_user.id,
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


@router.post("/test")
async def test_retrieval(
    request: RAGTestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test RAG retrieval with a query."""
    rag_service = RAGService(
        db,
        embedding_provider=request.embedding_provider,
        embedding_model=request.embedding_model
    )

    try:
        chunks = await rag_service.retrieve_relevant_chunks(
            query=request.query,
            collection_id=request.collection_id,
            top_k=request.top_k,
            score_threshold=request.score_threshold,
            search_method=request.search_method
        )

        context = await rag_service.format_rag_context(chunks)

        return {
            "success": True,
            "chunks": chunks,
            "context": context,
            "total_retrieved": len(chunks)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### 4.2 Register RAG Router
**File:** `backend/app/main.py`

```python
from app.api.v1 import rag

app.include_router(rag.router, prefix="/api/v1/rag", tags=["rag"])
```

---

## Installation & Setup

### 1. Install Python Dependencies
```bash
pip install pgvector
pip install psycopg[binary]
pip install langchain-openai
pip install langchain-anthropic
pip install langchain-google-genai
```

### 2. Create Vector Index
```bash
python -c "
import psycopg

conn = psycopg.connect('postgresql://demystrag_user:demystrag_password@localhost:5433/demystrag')
cur = conn.cursor()

# Create HNSW index
cur.execute('''
CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx
ON document_chunks
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64)
''')

conn.commit()
print('Vector index created successfully!')
"
```

### 3. Update Requirements
Add to `backend/requirements.txt`:
```
pgvector==0.3.5
psycopg[binary]==3.2.3
langchain-openai>=0.2.0
langchain-anthropic>=0.2.0
langchain-google-genai>=2.0.0
```

---

## Usage Example

### 1. Configure RAG Retriever Node
1. Drag RAG_RETRIEVER node onto canvas
2. Connect from LLM_AGENT bottom handle (purple) to RAG node top handle
3. Configure in PropertyPanel:
   - **Collection**: Select document collection
   - **Embedding Provider**: openai
   - **Embedding Model**: text-embedding-ada-002
   - **Search Method**: cosine
   - **Top K**: 5
   - **Score Threshold**: 0.7

### 2. Test Retrieval
Use the test endpoint to verify:
```bash
curl -X POST http://localhost:8000/api/v1/rag/test \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "query": "What is the pricing model?",
    "collection_id": 1,
    "top_k": 5,
    "score_threshold": 0.7
  }'
```

### 3. Run Agent with RAG
The LLM agent will automatically:
1. Detect RAG connection
2. Generate embedding for user query
3. Search vector database
4. Inject top K chunks as context
5. Generate response using RAG context

---

## Performance Optimization

### Index Tuning
- **HNSW parameters**:
  - `m = 16`: Good default (use 32 for higher recall)
  - `ef_construction = 64`: Good default (use 128 for better quality)

- **Query time tuning**:
  ```sql
  SET hnsw.ef_search = 100;  -- Higher = better recall, slower
  ```

### Chunking Strategy
Current setup assumes documents are already chunked. For optimal retrieval:
- **Chunk size**: 500-1000 tokens
- **Overlap**: 100-200 tokens
- **Metadata**: Include source, page number, section

### Caching
Consider caching embeddings for frequently used queries:
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
async def get_cached_embedding(query: str):
    return await embeddings.aembed_query(query)
```

---

## Testing Checklist

- [ ] Vector index created successfully
- [ ] Collections API returns data
- [ ] Test retrieval endpoint works
- [ ] RAG node configuration UI loads collections
- [ ] LLM agent detects RAG connection
- [ ] Context is injected into LLM prompt
- [ ] Response quality improved with RAG

---

## Troubleshooting

### Issue: "pgvector extension not found"
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Issue: "No chunks retrieved"
- Check if documents exist in collection
- Lower score_threshold
- Verify embedding model matches data

### Issue: "Slow retrieval"
- Create/rebuild vector index
- Increase `hnsw.ef_search` parameter
- Use IVFFlat index for large datasets

---

## Future Enhancements

1. **Hybrid Search**: Combine vector + keyword (BM25)
2. **Reranking**: Add cross-encoder reranker for better relevance
3. **Query Expansion**: Expand query with synonyms/related terms
4. **Document Upload**: Add UI for uploading documents to collections
5. **Multi-Query**: Generate multiple query variations for better coverage
6. **Citation**: Track which chunks were used in response
