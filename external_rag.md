# External API Integration Guide

This guide explains how to integrate external systems (n8n, custom apps, chatbots) with DemystRAG using API keys.

## Base URL

```
http://localhost:8003
```

## Authentication

Add the API key to your requests using one of these headers:

```
X-API-Key: dmr_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

or

```
Authorization: Bearer dmr_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## Available Endpoints

### 1. Search Collections (RAG Query)

Perform vector similarity search across your documents.

```bash
POST /api/v1/search
Content-Type: application/json
X-API-Key: dmr_xxxxx...
```

**Request Body:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| query | string | Yes | - | Search query text |
| top_k | integer | No | 5 | Number of results to return |
| similarity_threshold | float | No | 0.7 | Minimum similarity score (0-1) |
| collection_id | integer | No | - | Filter by specific collection |
| document_ids | array | No | - | Filter by specific document IDs |

**Example Request:**

```json
{
  "query": "What is machine learning?",
  "top_k": 5,
  "similarity_threshold": 0.7,
  "collection_id": 3
}
```

**Example Response:**

```json
{
  "chunks": [
    {
      "id": 1,
      "document_id": 5,
      "text": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed.",
      "chunk_index": 0,
      "provider": "openai",
      "model": "text-embedding-3-small",
      "similarity": 0.92
    },
    {
      "id": 2,
      "document_id": 5,
      "text": "There are three main types of machine learning: supervised, unsupervised, and reinforcement learning.",
      "chunk_index": 1,
      "provider": "openai",
      "model": "text-embedding-3-small",
      "similarity": 0.87
    }
  ],
  "query_time_ms": 45.2,
  "total_chunks": 2
}
```

---

### 2. List Collections

Get all collections in your organization.

```bash
GET /api/v1/collections
X-API-Key: dmr_xxxxx...
```

**Example Response:**

```json
{
  "collections": [
    {
      "id": 3,
      "name": "Technical Docs",
      "description": "Product documentation and guides",
      "document_count": 15,
      "embedding_provider": "openai",
      "embedding_model": "text-embedding-3-small",
      "created_at": "2024-12-09T10:30:00"
    },
    {
      "id": 4,
      "name": "Knowledge Base",
      "description": "Internal knowledge articles",
      "document_count": 42,
      "embedding_provider": "openai",
      "embedding_model": "text-embedding-3-small",
      "created_at": "2024-12-10T14:15:00"
    }
  ],
  "total": 2,
  "organization_id": 1,
  "organization_name": "Acme Corp"
}
```

---

### 3. Get Collection Details

Get details of a specific collection.

```bash
GET /api/v1/collections/{collection_id}
X-API-Key: dmr_xxxxx...
```

**Example Response:**

```json
{
  "id": 3,
  "name": "Technical Docs",
  "description": "Product documentation and guides",
  "document_count": 15,
  "embedding_provider": "openai",
  "embedding_model": "text-embedding-3-small",
  "created_at": "2024-12-09T10:30:00"
}
```

---

### 4. List Documents in Collection

Get all documents in a specific collection.

```bash
GET /api/v1/collections/{collection_id}/documents
X-API-Key: dmr_xxxxx...
```

**Example Response:**

```json
{
  "collection_id": 3,
  "collection_name": "Technical Docs",
  "documents": [
    {
      "id": 10,
      "filename": "user-guide.pdf",
      "file_type": "pdf",
      "chunk_count": 25,
      "uploaded_at": "2024-12-09T11:00:00"
    },
    {
      "id": 11,
      "filename": "api-reference.md",
      "file_type": "md",
      "chunk_count": 18,
      "uploaded_at": "2024-12-09T11:30:00"
    }
  ],
  "total": 2
}
```

---

### 5. List All Documents

Get all documents in your organization.

```bash
GET /api/v1/documents
X-API-Key: dmr_xxxxx...
```

**Optional Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| collection_id | integer | Filter by collection |

**Example with filter:**

```bash
GET /api/v1/documents?collection_id=3
X-API-Key: dmr_xxxxx...
```

**Example Response:**

```json
{
  "documents": [
    {
      "id": 10,
      "filename": "user-guide.pdf",
      "file_type": "pdf",
      "collection_id": 3,
      "chunk_count": 25,
      "uploaded_at": "2024-12-09T11:00:00"
    }
  ],
  "total": 1,
  "organization_id": 1
}
```

---

## Code Examples

### Python

```python
import requests

API_URL = "http://localhost:8003"
API_KEY = "dmr_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Search for relevant context
def search_rag(query: str, top_k: int = 5, collection_id: int = None):
    payload = {
        "query": query,
        "top_k": top_k
    }
    if collection_id:
        payload["collection_id"] = collection_id

    response = requests.post(
        f"{API_URL}/api/v1/search",
        headers=headers,
        json=payload
    )
    response.raise_for_status()
    return response.json()

# List collections
def list_collections():
    response = requests.get(
        f"{API_URL}/api/v1/collections",
        headers=headers
    )
    response.raise_for_status()
    return response.json()

# Example usage
results = search_rag("What is machine learning?", top_k=5)
for chunk in results["chunks"]:
    print(f"[Score: {chunk['similarity']:.2f}] {chunk['text'][:100]}...")
```

### JavaScript / Node.js

```javascript
const API_URL = "http://localhost:8003";
const API_KEY = "dmr_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx";

const headers = {
  "X-API-Key": API_KEY,
  "Content-Type": "application/json"
};

// Search for relevant context
async function searchRAG(query, topK = 5, collectionId = null) {
  const payload = { query, top_k: topK };
  if (collectionId) payload.collection_id = collectionId;

  const response = await fetch(`${API_URL}/api/v1/search`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`Search failed: ${response.statusText}`);
  }

  return response.json();
}

// List collections
async function listCollections() {
  const response = await fetch(`${API_URL}/api/v1/collections`, { headers });
  return response.json();
}

// Example usage
const results = await searchRAG("What is machine learning?", 5);
results.chunks.forEach(chunk => {
  console.log(`[${chunk.similarity.toFixed(2)}] ${chunk.text.substring(0, 100)}...`);
});
```

### cURL

```bash
# Search
curl -X POST http://localhost:8003/api/v1/search \
  -H "X-API-Key: dmr_xxxxx..." \
  -H "Content-Type: application/json" \
  -d '{
    "query": "machine learning",
    "top_k": 5,
    "collection_id": 3
  }'

# List collections
curl http://localhost:8003/api/v1/collections \
  -H "X-API-Key: dmr_xxxxx..."

# List documents
curl http://localhost:8003/api/v1/documents \
  -H "X-API-Key: dmr_xxxxx..."

# List documents in collection
curl http://localhost:8003/api/v1/collections/3/documents \
  -H "X-API-Key: dmr_xxxxx..."
```

---

## n8n Integration

### HTTP Request Node Configuration

**For Search:**

| Field | Value |
|-------|-------|
| Method | POST |
| URL | `http://localhost:8003/api/v1/search` |
| Authentication | None (use headers) |
| Headers | `X-API-Key`: `dmr_xxxxx...` |
| | `Content-Type`: `application/json` |
| Body Type | JSON |
| Body | See below |

**Body:**
```json
{
  "query": "{{ $json.user_question }}",
  "top_k": 5,
  "collection_id": 3
}
```

**For List Collections:**

| Field | Value |
|-------|-------|
| Method | GET |
| URL | `http://localhost:8003/api/v1/collections` |
| Headers | `X-API-Key`: `dmr_xxxxx...` |

### Example n8n Workflow

1. **Webhook Node** - Receive user question
2. **HTTP Request Node** - Call `/api/v1/search` with the question
3. **Code Node** - Format the chunks into context
4. **OpenAI Node** - Send context + question to GPT for response
5. **Respond to Webhook** - Return the answer

---

## Error Responses

| Status Code | Description | Example |
|-------------|-------------|---------|
| 401 | Invalid or missing API key | `{"detail": "Invalid or expired API key"}` |
| 403 | Organization is inactive | `{"detail": "Organization is inactive"}` |
| 404 | Resource not found | `{"detail": "Collection not found"}` |
| 422 | Invalid request body | `{"detail": "Query is required"}` |
| 500 | Server error | `{"detail": "Internal server error"}` |

---

## Getting an API Key

1. Login to the DemystRAG web UI as an organization admin
2. Navigate to **Organization Settings**
3. Scroll down to the **API Keys** section
4. Click **Create API Key**
5. Enter a name (e.g., "n8n Production")
6. Click **Create**
7. **Copy the key immediately** - it's only shown once!

---

## Best Practices

1. **Store keys securely** - Use environment variables, never hardcode
2. **Use collection_id** - Filter searches to specific collections for better results
3. **Adjust similarity_threshold** - Lower for broader results, higher for precision
4. **Set appropriate top_k** - Balance between context quality and token usage
5. **Monitor last_used_at** - Track which keys are actively being used
6. **Rotate keys periodically** - Use the regenerate feature for security

---

## Rate Limits

Currently, there are no rate limits enforced. This may change in future versions based on your organization's plan tier.

---

## Support

For issues or questions:
- Check the API key is active in Organization Settings
- Verify the collection exists and has documents
- Ensure documents have been processed with embeddings
