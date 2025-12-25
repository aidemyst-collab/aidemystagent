# LLM Agent Enhancement Proposal

## Executive Summary

This document proposes comprehensive enhancements to the LLM_AGENT node to support advanced agent capabilities including memory management, dynamic tool binding, RAG integration, and improved model configuration. The design is inspired by n8n's AI Agent architecture and LangChain/LangGraph patterns.

---

## Current State Analysis

### What's Already Implemented

**LLM_AGENT Node Configuration:**
- ✅ Credential selection (multi-provider support)
- ✅ Model selection (GPT-4, Claude, etc.)
- ✅ Temperature and max tokens
- ✅ System prompt
- ✅ Static tool list selection

**Backend:**
- ✅ Placeholder LLM handler in `langgraph_engine.py`
- ✅ Credential model with multi-provider support
- ✅ Tool registry with built-in tools
- ✅ AgentState management in LangGraph

**Missing Critical Features:**
- ❌ Actual LLM API integration
- ❌ Memory/conversation history management
- ❌ Dynamic tool binding from TOOL nodes
- ❌ RAG retriever integration with context injection
- ❌ Agent type selection (ReAct, Function Calling, etc.)
- ❌ Streaming response support
- ❌ Token usage tracking

---

## Proposed Architecture

### 1. Node Connection Pattern (n8n-inspired)

```
┌─────────────┐
│   INPUT     │
└──────┬──────┘
       │
       ↓
┌─────────────┐      ┌──────────────┐
│  MEMORY     │─────→│  LLM_AGENT   │
└─────────────┘      └──────┬───────┘
                            │
       ┌────────────────────┼────────────────┐
       │                    │                │
       ↓                    ↓                ↓
┌──────────┐         ┌──────────┐    ┌─────────────┐
│   TOOL   │────────→│   TOOL   │    │RAG_RETRIEVER│
└──────────┘         └──────────┘    └─────────────┘
       │                    │                │
       └────────────────────┼────────────────┘
                            ↓
                     ┌─────────────┐
                     │   OUTPUT    │
                     └─────────────┘
```

**Connection Rules:**
- **INPUT → LLM_AGENT**: Provides user query
- **MEMORY → LLM_AGENT**: Injects conversation history
- **TOOL → LLM_AGENT**: Makes tool available for agent to call
- **RAG_RETRIEVER → LLM_AGENT**: Provides context documents
- **LLM_AGENT → OUTPUT**: Returns agent response

---

## Feature 1: Enhanced Model Configuration

### Current Implementation
```typescript
{
  credentialId: "uuid",
  modelConfig: {
    model: "gpt-4",
    temperature: 0.7,
    maxTokens: 2048
  },
  systemPrompt: "You are a helpful assistant"
}
```

### Proposed Enhancements

```typescript
interface LLMAgentConfig {
  // Credential & Model
  credentialId: string;
  modelConfig: {
    model: string;
    temperature?: number;
    maxTokens?: number;
    topP?: number;
    frequencyPenalty?: number;
    presencePenalty?: number;
    stopSequences?: string[];
  };

  // Agent Type
  agentType: 'react' | 'openai-functions' | 'conversational' | 'tools' | 'structured-chat';

  // Prompting
  systemPrompt?: string;
  humanMessageTemplate?: string; // Template for formatting user input
  prefixMessages?: Array<{ role: 'system' | 'user' | 'assistant'; content: string }>;

  // Behavior
  maxIterations?: number; // Max tool calling loops (default: 5)
  returnIntermediateSteps?: boolean; // Return tool calls in response
  earlyStoppingMethod?: 'force' | 'generate'; // How to stop iteration

  // Response Formatting
  outputParser?: 'default' | 'json' | 'structured';
  outputSchema?: object; // JSON schema for structured output

  // Streaming
  enableStreaming?: boolean;

  // Advanced
  llmKwargs?: Record<string, any>; // Provider-specific parameters
}
```

### Backend Changes

```python
# backend/app/services/llm_client.py
from typing import Optional, AsyncIterator
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage
from app.models.credential import Credential

class LLMClient:
    """Unified LLM client for all providers."""

    @staticmethod
    async def create_client(credential: Credential, model_config: dict):
        """Create appropriate LLM client based on credential provider."""
        provider = credential.provider
        api_key = credential.api_key

        base_params = {
            "model": model_config.get("model"),
            "temperature": model_config.get("temperature", 0.7),
            "max_tokens": model_config.get("maxTokens", 2048),
        }

        if provider == "openai":
            return ChatOpenAI(
                api_key=api_key,
                base_url=credential.config.get("base_url"),
                **base_params
            )
        elif provider == "anthropic":
            return ChatAnthropic(
                api_key=api_key,
                **base_params
            )
        elif provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                google_api_key=api_key,
                **base_params
            )
        # Add more providers...

        raise ValueError(f"Unsupported provider: {provider}")

    @staticmethod
    async def invoke(
        client,
        messages: list[BaseMessage],
        tools: Optional[list] = None,
        stream: bool = False
    ):
        """Invoke LLM with optional tool binding."""
        if tools:
            client = client.bind_tools(tools)

        if stream:
            return client.astream(messages)
        else:
            return await client.ainvoke(messages)
```

---

## Feature 2: Memory Node

### Purpose
Store and retrieve conversation history to maintain context across turns.

### New Node Type: MEMORY

**Visual Properties:**
- Icon: 💭 (Brain/Memory icon)
- Color: `#fa8c16` (Orange)
- Has Input: Yes (from previous conversation)
- Has Output: Yes (to LLM_AGENT)

### Configuration Schema

```typescript
interface MemoryNodeConfig {
  // Memory Type
  type: 'buffer' | 'buffer-window' | 'summary' | 'vector' | 'entity';

  // Buffer Window Memory
  windowSize?: number; // Number of recent messages to keep (default: 10)

  // Summary Memory
  summaryModel?: string; // Model to use for summarization
  maxTokenThreshold?: number; // When to trigger summarization

  // Vector Memory
  vectorStore?: {
    provider: 'pinecone' | 'qdrant' | 'redis' | 'postgres';
    endpoint: string;
    apiKey?: string;
    topK?: number; // Number of relevant messages to retrieve
  };

  // Entity Memory
  entityExtraction?: {
    enabled: boolean;
    entitiesToTrack: string[]; // e.g., ['user_name', 'user_preferences']
  };

  // Storage
  persistence?: {
    enabled: boolean;
    sessionIdField?: string; // Field in input to use as session ID
    backend: 'redis' | 'postgres' | 'mongodb';
  };

  // Context
  memoryKey?: string; // Key to store memory in state (default: 'chat_history')
  returnMessages?: boolean; // Return as message objects vs strings
  inputKey?: string; // Key from input to use (default: 'input')
  outputKey?: string; // Key from output to store (default: 'output')
}
```

### Backend Implementation

```python
# backend/app/services/memory_manager.py
from typing import List, Optional
from langchain.memory import (
    ConversationBufferMemory,
    ConversationBufferWindowMemory,
    ConversationSummaryMemory,
    VectorStoreRetrieverMemory,
    ConversationEntityMemory
)
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from app.models.agent import AgentExecution
import redis
import json

class MemoryManager:
    """Manages conversation memory for agents."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def create_memory(self, config: dict, llm=None):
        """Create memory instance based on configuration."""
        memory_type = config.get("type", "buffer-window")

        if memory_type == "buffer":
            return ConversationBufferMemory(
                return_messages=config.get("returnMessages", True),
                memory_key=config.get("memoryKey", "chat_history"),
                input_key=config.get("inputKey", "input"),
                output_key=config.get("outputKey", "output"),
            )

        elif memory_type == "buffer-window":
            return ConversationBufferWindowMemory(
                k=config.get("windowSize", 10),
                return_messages=config.get("returnMessages", True),
                memory_key=config.get("memoryKey", "chat_history"),
            )

        elif memory_type == "summary":
            return ConversationSummaryMemory(
                llm=llm,
                return_messages=config.get("returnMessages", True),
                memory_key=config.get("memoryKey", "chat_history"),
            )

        # Add vector and entity memory types...

    async def load_session_memory(
        self,
        session_id: str,
        config: dict
    ) -> List[BaseMessage]:
        """Load conversation history from persistent storage."""
        if not config.get("persistence", {}).get("enabled"):
            return []

        backend = config.get("persistence", {}).get("backend", "redis")

        if backend == "redis":
            key = f"memory:session:{session_id}"
            data = self.redis.get(key)
            if data:
                messages_data = json.loads(data)
                return [
                    HumanMessage(content=m["content"]) if m["role"] == "user"
                    else AIMessage(content=m["content"])
                    for m in messages_data
                ]
        # Add postgres, mongodb backends...

        return []

    async def save_session_memory(
        self,
        session_id: str,
        messages: List[BaseMessage],
        config: dict
    ):
        """Save conversation history to persistent storage."""
        if not config.get("persistence", {}).get("enabled"):
            return

        backend = config.get("persistence", {}).get("backend", "redis")

        if backend == "redis":
            key = f"memory:session:{session_id}"
            messages_data = [
                {
                    "role": "user" if isinstance(m, HumanMessage) else "assistant",
                    "content": m.content
                }
                for m in messages
            ]
            self.redis.setex(
                key,
                86400 * 7,  # 7 days TTL
                json.dumps(messages_data)
            )
        # Add postgres, mongodb backends...

    async def get_memory_variables(
        self,
        memory: Any,
        session_id: Optional[str] = None,
        config: dict = {}
    ) -> dict:
        """Get memory variables to inject into LLM context."""
        if session_id and config.get("persistence", {}).get("enabled"):
            # Load from persistent storage
            history = await self.load_session_memory(session_id, config)
            return {
                config.get("memoryKey", "chat_history"): history
            }
        else:
            # Use in-memory instance
            return memory.load_memory_variables({})
```

### LangGraph Integration

```python
# In langgraph_engine.py

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    agent_config: dict
    current_node: str
    execution_path: list
    tool_results: dict
    final_output: Optional[str]
    raw_input: Any
    processed_input: Optional[Dict]
    input_metadata: Optional[Dict]
    # NEW: Memory support
    chat_history: Optional[List[BaseMessage]]  # Conversation history
    session_id: Optional[str]  # Session identifier
    memory_context: Optional[Dict]  # Additional memory context (entities, summary)


def _handle_memory_node(self, state: AgentState) -> AgentState:
    """Handle MEMORY node - load and inject conversation history."""
    state["execution_path"].append("MEMORY")

    # Get memory node configuration
    node_config = self._get_node_config(state, "MEMORY")

    # Get or generate session ID
    session_id = state.get("session_id") or state.get("processed_input", {}).get("session_id")

    if session_id:
        # Load memory from persistent storage
        memory_manager = MemoryManager(self.redis_client)
        memory = await memory_manager.create_memory(node_config, self.llm_client)

        # Load session history
        history = await memory_manager.load_session_memory(session_id, node_config)

        state["chat_history"] = history
        state["session_id"] = session_id
    else:
        # In-memory only (no persistence)
        state["chat_history"] = []

    return state


def _handle_llm_agent_node(self, state: AgentState) -> AgentState:
    """Enhanced LLM_AGENT node with memory and tool support."""
    state["execution_path"].append("LLM_AGENT")

    # Get node configuration
    node_config = self._get_node_config(state, "LLM_AGENT")

    # Build message list
    messages = []

    # 1. Add system prompt
    if system_prompt := node_config.get("systemPrompt"):
        messages.append(SystemMessage(content=system_prompt))

    # 2. Inject conversation history from memory
    if chat_history := state.get("chat_history"):
        messages.extend(chat_history)

    # 3. Inject RAG context (if available)
    if rag_context := state.get("tool_results", {}).get("rag_retrieval"):
        context_prompt = f"Use the following context to answer:\n\n{rag_context}"
        messages.append(SystemMessage(content=context_prompt))

    # 4. Add current user message
    messages.extend(state["messages"])

    # Get credential and create LLM client
    credential_id = node_config.get("credentialId")
    credential = await self.db.get(Credential, credential_id)

    llm_client = await LLMClient.create_client(
        credential,
        node_config.get("modelConfig", {})
    )

    # Bind tools if available
    tools = self._get_connected_tools(state)
    if tools:
        llm_client = llm_client.bind_tools(tools)

    # Invoke LLM
    response = await llm_client.ainvoke(messages)

    # Update state
    state["messages"].append(response)

    # Save to memory if configured
    if session_id := state.get("session_id"):
        memory_manager = MemoryManager(self.redis_client)
        updated_history = (state.get("chat_history") or []) + [
            state["messages"][0],  # User message
            response  # AI response
        ]
        await memory_manager.save_session_memory(
            session_id,
            updated_history,
            self._get_node_config(state, "MEMORY")
        )

    return state
```

---

## Feature 3: Tool Node Connection

### Current State
Tools are selected via a static dropdown in LLM_AGENT config. Tools are not connected as separate nodes.

### Proposed Enhancement
Tool nodes connect to LLM_AGENT nodes via edges, making tools dynamically available.

### Edge-Based Tool Binding

**Visual Pattern:**
```
┌──────────┐         ┌─────────────┐
│   TOOL   │────────→│  LLM_AGENT  │
│Calculator│         │             │
└──────────┘         └─────────────┘
                            ↑
┌──────────┐                │
│   TOOL   │────────────────┘
│WebSearch │
└──────────┘
```

### Implementation Strategy

```python
def _get_connected_tools(self, state: AgentState) -> List:
    """Get tools connected to LLM_AGENT node via edges."""
    agent_config = state["agent_config"]
    nodes = agent_config.get("nodes", [])
    edges = agent_config.get("edges", [])

    # Find LLM_AGENT node
    llm_node = next((n for n in nodes if n.get("data", {}).get("type") == "LLM_AGENT"), None)
    if not llm_node:
        return []

    llm_node_id = llm_node["id"]

    # Find all TOOL nodes connected to this LLM_AGENT
    connected_tool_ids = [
        edge["source"]
        for edge in edges
        if edge["target"] == llm_node_id and
           self._get_node_by_id(nodes, edge["source"]).get("data", {}).get("type") == "TOOL"
    ]

    # Load tool instances
    tools = []
    for tool_node_id in connected_tool_ids:
        tool_node = self._get_node_by_id(nodes, tool_node_id)
        tool_config = tool_node.get("data", {}).get("config", {})

        # Get tool from registry or database
        tool_id = tool_config.get("toolId")
        if tool_id:
            tool_instance = await self._load_tool(tool_id)
            if tool_instance:
                tools.append(tool_instance)

    return tools


async def _load_tool(self, tool_id: str):
    """Load tool instance from registry or database."""
    # Check built-in tools
    from app.services.tools import tool_registry

    builtin_tool = tool_registry.get_tool(tool_id)
    if builtin_tool:
        return builtin_tool.to_langchain_tool()

    # Check custom tools in database
    tool = await self.db.get(Tool, tool_id)
    if tool:
        return self._create_custom_tool(tool)

    return None
```

### Tool Node Configuration Enhancement

```typescript
interface ToolNodeConfig {
  // Tool Selection
  toolSource: 'built-in' | 'custom' | 'api';

  // Built-in Tool
  builtInToolId?: string; // calculator, web_search, datetime, etc.

  // Custom Tool (from database)
  customToolId?: string; // UUID of custom tool

  // API Tool
  apiConfig?: {
    name: string;
    description: string;
    endpoint: string;
    method: 'GET' | 'POST' | 'PUT' | 'DELETE';
    headers?: Record<string, string>;
    bodyTemplate?: string; // Template for request body
    responseMapping?: string; // JMESPath to extract result
  };

  // Parameters (overrides)
  parameters?: Record<string, any>;

  // Error Handling
  retryOnFailure?: boolean;
  maxRetries?: number;
  timeoutMs?: number;
}
```

---

## Feature 4: RAG Retriever Integration

### Current State
RAG_RETRIEVER node exists but doesn't inject context into LLM_AGENT.

### Proposed Enhancement
RAG retriever results are automatically injected as context into connected LLM agents.

### Architecture

```
┌─────────────────┐
│  RAG_RETRIEVER  │
│  (Vector Store) │
└────────┬────────┘
         │ Retrieves relevant docs
         │ based on user query
         ↓
  ┌─────────────┐
  │  LLM_AGENT  │ ← Context injected into prompt
  └─────────────┘
```

### Implementation

```python
def _handle_rag_retriever_node(self, state: AgentState) -> AgentState:
    """Handle RAG_RETRIEVER node - retrieve from knowledge base."""
    state["execution_path"].append("RAG_RETRIEVER")

    # Get node configuration
    node_config = self._get_node_config(state, "RAG_RETRIEVER")

    # Get user query (from current message or processed input)
    query = state["messages"][-1].content if state["messages"] else state.get("processed_input", {}).get("message", "")

    # Retrieve relevant documents
    retriever = await self._create_retriever(node_config)
    documents = await retriever.aget_relevant_documents(query)

    # Format context
    context = "\n\n".join([
        f"Document {i+1}:\n{doc.page_content}"
        for i, doc in enumerate(documents)
    ])

    # Store in state for LLM to use
    state["tool_results"]["rag_retrieval"] = {
        "context": context,
        "documents": [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": getattr(doc, "score", None)
            }
            for doc in documents
        ],
        "num_documents": len(documents),
    }

    return state


async def _create_retriever(self, config: dict):
    """Create vector store retriever from configuration."""
    provider = config.get("provider", "pinecone")
    endpoint = config.get("endpoint")
    api_key = config.get("apiKey")
    top_k = config.get("topK", 5)

    if provider == "pinecone":
        from langchain_pinecone import PineconeVectorStore
        from langchain_openai import OpenAIEmbeddings

        vectorstore = PineconeVectorStore(
            index_name=config.get("indexName"),
            embedding=OpenAIEmbeddings(),
            pinecone_api_key=api_key
        )
        return vectorstore.as_retriever(search_kwargs={"k": top_k})

    elif provider == "qdrant":
        from langchain_qdrant import QdrantVectorStore
        # Similar setup...

    # Add more providers...

    raise ValueError(f"Unsupported RAG provider: {provider}")
```

### RAG Node Configuration Enhancement

```typescript
interface RAGRetrieverNodeConfig {
  // Provider
  provider: 'pinecone' | 'qdrant' | 'weaviate' | 'postgres-pgvector' | 'redis' | 'custom';

  // Connection
  endpoint?: string;
  apiKey?: string;
  indexName?: string;

  // Retrieval Settings
  topK?: number; // Number of documents to retrieve (default: 5)
  scoreThreshold?: number; // Minimum relevance score (0-1)
  searchType?: 'similarity' | 'mmr' | 'similarity-score-threshold';

  // MMR (Maximal Marginal Relevance) Settings
  mmr?: {
    enabled: boolean;
    fetchK?: number; // Fetch more docs than k for diversity
    lambdaMult?: number; // 0 = max diversity, 1 = max relevance
  };

  // Embeddings
  embeddingModel?: {
    provider: 'openai' | 'huggingface' | 'cohere';
    model: string;
    credentialId?: string;
  };

  // Metadata Filtering
  metadataFilter?: Record<string, any>; // Filter documents by metadata

  // Context Formatting
  contextTemplate?: string; // How to format retrieved docs
  includeMetadata?: boolean;
  includeScores?: boolean;

  // Advanced
  rerank?: {
    enabled: boolean;
    model?: string; // Cohere rerank, etc.
  };
}
```

---

## Feature 5: Agent Type Selection

### Supported Agent Types

Based on LangChain/LangGraph patterns:

1. **ReAct Agent** (Default)
   - Reasoning + Acting loop
   - Best for complex multi-step tasks
   - Uses scratchpad for thinking

2. **OpenAI Functions Agent**
   - Uses OpenAI function calling
   - More structured tool usage
   - Faster, more reliable

3. **Conversational Agent**
   - Optimized for chat
   - Maintains context naturally
   - Less focused on tool usage

4. **Tools Agent**
   - Simple tool executor
   - Direct tool → response
   - No complex reasoning

5. **Structured Chat**
   - For structured inputs/outputs
   - Schema-based responses
   - Data extraction focused

### Configuration

```typescript
interface AgentTypeConfig {
  type: 'react' | 'openai-functions' | 'conversational' | 'tools' | 'structured-chat';

  // ReAct specific
  react?: {
    maxIterations: number;
    observationPrefix?: string;
    thoughtPrefix?: string;
  };

  // OpenAI Functions specific
  openAiFunctions?: {
    parallelToolCalls?: boolean;
    strictMode?: boolean;
  };

  // Structured Chat specific
  structuredChat?: {
    outputSchema: object; // JSON Schema
    responseFormat?: 'json_object' | 'json_schema';
  };
}
```

---

## Implementation Roadmap

### Phase 1: LLM Integration (Week 1)
- [ ] Implement `LLMClient` service
- [ ] Connect credentials to LLM providers
- [ ] Update `_handle_llm_agent_node` with actual LLM calls
- [ ] Add streaming support
- [ ] Implement token usage tracking

### Phase 2: Memory System (Week 2)
- [ ] Create MEMORY node type
- [ ] Implement `MemoryManager` service
- [ ] Add Redis-based session storage
- [ ] Update PropertyPanel for MEMORY config
- [ ] Integrate memory into LLM_AGENT handler

### Phase 3: Tool Integration (Week 2)
- [ ] Implement edge-based tool discovery
- [ ] Update `_get_connected_tools` method
- [ ] Convert built-in tools to LangChain tools
- [ ] Add tool execution tracking
- [ ] Update PropertyPanel for TOOL config

### Phase 4: RAG Integration (Week 3)
- [ ] Implement `_create_retriever` method
- [ ] Add vector store connectors (Pinecone, Qdrant)
- [ ] Update `_handle_rag_retriever_node`
- [ ] Implement context injection into LLM
- [ ] Update PropertyPanel for RAG config

### Phase 5: Agent Types (Week 3-4)
- [ ] Implement ReAct agent pattern
- [ ] Implement OpenAI Functions agent
- [ ] Add agent type selector in PropertyPanel
- [ ] Update execution engine for different agent types
- [ ] Add iteration tracking and limits

### Phase 6: Testing & Polish (Week 4)
- [ ] End-to-end testing with all node types
- [ ] Performance optimization
- [ ] Error handling improvements
- [ ] Documentation

---

## Database Schema Updates

### New Table: `conversation_sessions`

```sql
CREATE TABLE conversation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    agent_id UUID REFERENCES agents(id),
    session_key VARCHAR(255) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    UNIQUE(agent_id, session_key)
);

CREATE TABLE conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL, -- 'user' or 'assistant'
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX(session_id, created_at)
);
```

### Update Existing Tables

```sql
-- Add agent_type to agent config
ALTER TABLE agents ADD COLUMN agent_type VARCHAR(50) DEFAULT 'react';

-- Add token tracking to executions
ALTER TABLE agent_executions
    ADD COLUMN prompt_tokens INTEGER DEFAULT 0,
    ADD COLUMN completion_tokens INTEGER DEFAULT 0,
    ADD COLUMN total_tokens INTEGER DEFAULT 0,
    ADD COLUMN cost_cents INTEGER DEFAULT 0;
```

---

## Impact Analysis

### Benefits

1. **Statefulness**: Memory enables multi-turn conversations
2. **Modularity**: Tool/RAG nodes can be reused across agents
3. **Flexibility**: Different agent types for different use cases
4. **Observability**: Track tool usage, iterations, token consumption
5. **n8n Compatibility**: Familiar patterns for users coming from n8n

### Breaking Changes

**None** - All changes are additive:
- Existing agents without memory continue working
- Static tool selection still supported
- Default agent type is 'react'

### Performance Considerations

1. **Memory Overhead**: Redis storage for conversation history
2. **Tool Latency**: Network calls to external tools
3. **RAG Latency**: Vector search + embedding generation
4. **Token Costs**: More context = higher costs

**Mitigation:**
- Cache embeddings
- Parallel tool execution where possible
- Configurable memory window sizes
- Token usage warnings

---

## UI/UX Changes

### PropertyPanel Updates

**LLM_AGENT Node:**
```
┌────────────────────────────────┐
│ Agent Type: [ReAct ▼]          │
├────────────────────────────────┤
│ API Credential: [Select ▼]     │
│ Model: [GPT-4 ▼]               │
│ Temperature: [0.7]              │
│ Max Tokens: [2048]              │
├────────────────────────────────┤
│ System Prompt:                  │
│ [Text area]                     │
├────────────────────────────────┤
│ Advanced Settings:              │
│ ☐ Enable streaming             │
│ ☐ Return intermediate steps    │
│ Max Iterations: [5]             │
└────────────────────────────────┘
```

**MEMORY Node (New):**
```
┌────────────────────────────────┐
│ Memory Type: [Buffer Window ▼] │
├────────────────────────────────┤
│ Window Size: [10] messages      │
├────────────────────────────────┤
│ Persistence:                    │
│ ☑ Enable session persistence   │
│ Backend: [Redis ▼]             │
│ Session ID Field: [session_id] │
└────────────────────────────────┘
```

**TOOL Node Updates:**
```
┌────────────────────────────────┐
│ Tool Source: [Built-in ▼]      │
├────────────────────────────────┤
│ Select Tool: [Calculator ▼]    │
│                                 │
│ OR                              │
│                                 │
│ Custom Tool: [My Tool ▼]       │
├────────────────────────────────┤
│ Error Handling:                 │
│ ☑ Retry on failure             │
│ Max Retries: [3]                │
│ Timeout: [30000] ms             │
└────────────────────────────────┘
```

**RAG_RETRIEVER Updates:**
```
┌────────────────────────────────┐
│ Provider: [Pinecone ▼]          │
├────────────────────────────────┤
│ API Key: [Credential ▼]         │
│ Index Name: [my-index]          │
├────────────────────────────────┤
│ Retrieval Settings:             │
│ Top K: [5] documents            │
│ Score Threshold: [0.7]          │
│ Search Type: [Similarity ▼]    │
├────────────────────────────────┤
│ Advanced:                       │
│ ☑ Enable MMR (diversity)       │
│ ☐ Enable reranking             │
└────────────────────────────────┘
```

### Node Library Updates

Add MEMORY node to the node palette:
```typescript
{
  type: 'MEMORY',
  label: 'Memory',
  icon: '💭',
  color: '#fa8c16',
  category: 'Core',
  description: 'Store and retrieve conversation history'
}
```

---

## Testing Strategy

### Unit Tests
- LLMClient provider initialization
- MemoryManager session storage/retrieval
- Tool discovery from graph edges
- RAG context formatting

### Integration Tests
- LLM → Memory → LLM flow
- LLM + Tools execution
- LLM + RAG context injection
- Multi-turn conversations with memory

### End-to-End Tests
- Complete workflow: INPUT → MEMORY → LLM + TOOLS + RAG → OUTPUT
- Streaming responses
- Error handling and retries
- Token usage tracking

---

## Example Workflows

### Example 1: Customer Support Bot with Memory

```json
{
  "nodes": [
    {
      "id": "input-1",
      "type": "INPUT",
      "data": {
        "type": "INPUT",
        "config": { "mode": "chat" }
      }
    },
    {
      "id": "memory-1",
      "type": "MEMORY",
      "data": {
        "type": "MEMORY",
        "config": {
          "type": "buffer-window",
          "windowSize": 10,
          "persistence": { "enabled": true, "backend": "redis" }
        }
      }
    },
    {
      "id": "llm-1",
      "type": "LLM_AGENT",
      "data": {
        "type": "LLM_AGENT",
        "config": {
          "agentType": "conversational",
          "credentialId": "openai-cred",
          "modelConfig": { "model": "gpt-4", "temperature": 0.7 },
          "systemPrompt": "You are a helpful customer support agent."
        }
      }
    },
    {
      "id": "output-1",
      "type": "OUTPUT",
      "data": { "type": "OUTPUT" }
    }
  ],
  "edges": [
    { "source": "input-1", "target": "memory-1" },
    { "source": "memory-1", "target": "llm-1" },
    { "source": "llm-1", "target": "output-1" }
  ]
}
```

### Example 2: Research Agent with Tools and RAG

```json
{
  "nodes": [
    {
      "id": "input-1",
      "type": "INPUT",
      "data": {
        "type": "INPUT",
        "config": { "mode": "chat" }
      }
    },
    {
      "id": "rag-1",
      "type": "RAG_RETRIEVER",
      "data": {
        "type": "RAG_RETRIEVER",
        "config": {
          "provider": "pinecone",
          "indexName": "research-docs",
          "topK": 3
        }
      }
    },
    {
      "id": "tool-search",
      "type": "TOOL",
      "data": {
        "type": "TOOL",
        "config": {
          "toolSource": "built-in",
          "builtInToolId": "web_search"
        }
      }
    },
    {
      "id": "tool-calc",
      "type": "TOOL",
      "data": {
        "type": "TOOL",
        "config": {
          "toolSource": "built-in",
          "builtInToolId": "calculator"
        }
      }
    },
    {
      "id": "llm-1",
      "type": "LLM_AGENT",
      "data": {
        "type": "LLM_AGENT",
        "config": {
          "agentType": "react",
          "credentialId": "openai-cred",
          "modelConfig": { "model": "gpt-4", "temperature": 0 },
          "systemPrompt": "You are a research assistant. Use available tools and documents to answer questions accurately.",
          "maxIterations": 10
        }
      }
    },
    {
      "id": "output-1",
      "type": "OUTPUT",
      "data": { "type": "OUTPUT" }
    }
  ],
  "edges": [
    { "source": "input-1", "target": "rag-1" },
    { "source": "rag-1", "target": "llm-1" },
    { "source": "tool-search", "target": "llm-1" },
    { "source": "tool-calc", "target": "llm-1" },
    { "source": "llm-1", "target": "output-1" }
  ]
}
```

---

## Security Considerations

1. **API Key Storage**: Credentials encrypted at rest in database
2. **Tool Sandboxing**: Custom tools run in isolated environments
3. **Rate Limiting**: Per-user, per-agent execution limits
4. **Memory Isolation**: Sessions scoped to user + agent
5. **Tool Access Control**: Tools can be organization-scoped
6. **Prompt Injection**: Validate and sanitize system prompts

---

## Open Questions for Discussion

1. **Memory Storage**: Should we support PostgreSQL for memory in addition to Redis?
2. **Tool Marketplace**: Should we create a public tool marketplace?
3. **Agent Templates**: Pre-built agent workflows for common use cases?
4. **Cost Management**: Hard limits on token usage per execution?
5. **Multi-Agent**: Should we support agent-to-agent communication (SUBGRAPH with different agents)?
6. **Observability**: What level of debugging/tracing do we need (LangSmith integration)?

---

## Success Metrics

1. **Functionality**:
   - ✅ LLM calls working for all providers
   - ✅ Memory persists across sessions
   - ✅ Tools execute successfully
   - ✅ RAG context improves response quality

2. **Performance**:
   - < 3s average response time (without streaming)
   - < 500ms streaming first token
   - 95% tool execution success rate

3. **User Adoption**:
   - 50% of agents use memory
   - 30% of agents use RAG
   - 70% of agents use at least one tool

---

**Document Version**: 1.0
**Created**: 2025-11-30
**Author**: Claude (AgentStudio Enhancement Design)
**Status**: Awaiting Review
**Reference**: [n8n AI Agent Documentation](https://docs.n8n.io/integrations/builtin/cluster-nodes/root-nodes/n8n-nodes-langchain.agent/)
