from typing import TypedDict, Annotated, Sequence, Optional, Any, Dict, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
import operator
import json
import re
from datetime import datetime
from jsonschema import validate as json_validate, ValidationError as JsonValidationError
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.services.llm_client import LLMClient
from app.services.memory_manager import MemoryManager
from app.services.tool_converter import ToolConverter
from app.services.rag_service import RAGService
from app.services.template_engine import template_engine
from app.models.credential import Credential
from app.models.tool import Tool
import redis.asyncio as aioredis
from uuid import UUID

logger = logging.getLogger(__name__)


class NodeExecutionTrace(TypedDict):
    """Detailed execution trace for a single node."""
    node_id: str
    node_type: str
    node_label: str
    input_data: Optional[Dict[str, Any]]
    output_data: Optional[Dict[str, Any]]
    timestamp: str
    duration_ms: Optional[int]
    status: str  # 'success', 'error', 'skipped'
    error: Optional[str]
    metadata: Optional[Dict[str, Any]]


class AgentState(TypedDict):
    """State for the agent graph."""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    agent_config: dict
    current_node: str
    execution_path: list
    execution_trace: List[NodeExecutionTrace]  # Detailed execution tracking
    node_outputs: Dict[str, Dict[str, Any]]  # Store all node outputs for templating
    tool_results: dict
    final_output: Optional[str]
    # Enhanced input handling
    raw_input: Any
    processed_input: Optional[Dict]
    input_metadata: Optional[Dict]
    # LLM usage tracking
    llm_usage: Optional[Dict[str, int]]
    llm_cost: Optional[float]
    # Memory/conversation history
    chat_history: Optional[List[BaseMessage]]
    session_id: Optional[str]
    memory_context: Optional[Dict]


class StructuredOutputParser:
    """Parse and validate LLM outputs against schemas."""

    def __init__(self, config: Dict[str, Any]):
        self.parser_type = config.get('parserType', 'json_schema')
        self.schema = config.get('schema')
        self.strategy = config.get('strategy', 'lenient')
        self.error_handling = config.get('errorHandling', 'fail')
        self.type_coercion = config.get('typeCoercion', True)

        # Parse schema if it's a JSON string
        if isinstance(self.schema, str):
            try:
                self.schema = json.loads(self.schema)
            except json.JSONDecodeError:
                self.schema = {}

    def parse(self, llm_output: str) -> Dict[str, Any]:
        """Parse LLM output based on configuration."""
        try:
            # Step 1: Extract JSON from text
            parsed_json = self._extract_json(llm_output)

            # Step 2: Validate against schema
            if self.parser_type == 'json_schema' and self.schema:
                validated = self._validate_json_schema(parsed_json)
            else:
                validated = parsed_json

            # Step 3: Apply type coercion
            if self.type_coercion:
                validated = self._coerce_types(validated)

            return {
                'parsed_data': validated,
                'original_response': llm_output,
                'parsing_success': True,
                'validation_errors': [],
                'fields_extracted': list(validated.keys()) if isinstance(validated, dict) else []
            }

        except Exception as e:
            return self._handle_error(llm_output, e)

    def _extract_json(self, text: str) -> Dict:
        """Extract JSON from LLM response text."""
        # Try direct JSON parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Look for JSON in code blocks
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Look for JSON object anywhere in text
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        # If lenient, return empty dict
        if self.strategy == 'lenient':
            return {}

        raise ValueError("No valid JSON found in LLM output")

    def _validate_json_schema(self, data: Dict) -> Dict:
        """Validate data against JSON schema."""
        try:
            json_validate(instance=data, schema=self.schema)
            return data
        except JsonValidationError as e:
            if self.strategy == 'strict':
                raise
            elif self.strategy == 'lenient':
                # Return what we have, fill missing with defaults
                return self._apply_defaults(data)
            else:  # auto_fix
                # For now, just apply defaults
                return self._apply_defaults(data)

    def _coerce_types(self, data: Dict) -> Dict:
        """Coerce values to correct types based on schema."""
        if not self.schema or not isinstance(data, dict):
            return data

        coerced = {}
        properties = self.schema.get('properties', {})

        for key, value in data.items():
            expected_type = properties.get(key, {}).get('type')

            if expected_type:
                coerced[key] = self._convert_type(value, expected_type)
            else:
                coerced[key] = value

        return coerced

    def _convert_type(self, value: Any, target_type: str) -> Any:
        """Convert value to target type."""
        if value is None:
            return None

        try:
            if target_type == 'string':
                return str(value)
            elif target_type == 'number':
                return float(value) if '.' in str(value) else int(value)
            elif target_type == 'integer':
                return int(value)
            elif target_type == 'boolean':
                if isinstance(value, bool):
                    return value
                return str(value).lower() in ('true', '1', 'yes')
            elif target_type == 'array':
                return value if isinstance(value, list) else [value]
            else:
                return value
        except (ValueError, TypeError):
            return value

    def _apply_defaults(self, data: Dict) -> Dict:
        """Apply default values for missing fields."""
        if not self.schema:
            return data

        result = data.copy()
        properties = self.schema.get('properties', {})

        for field_name, field_schema in properties.items():
            if field_name not in result and 'default' in field_schema:
                result[field_name] = field_schema['default']

        return result

    def _handle_error(self, original: str, error: Exception) -> Dict:
        """Handle parsing errors based on configuration."""
        if self.error_handling == 'fail':
            raise error
        elif self.error_handling == 'pass_through':
            return {
                'parsed_data': {'raw_text': original},
                'original_response': original,
                'parsing_success': False,
                'validation_errors': [str(error)],
                'fields_extracted': []
            }
        elif self.error_handling == 'default_values':
            return {
                'parsed_data': self._apply_defaults({}),
                'original_response': original,
                'parsing_success': False,
                'validation_errors': [str(error)],
                'fields_extracted': []
            }
        else:
            raise error


class LangGraphEngine:
    """LangGraph-based agent execution engine."""

    def __init__(
        self,
        db: Optional[AsyncSession] = None,
        pgvector_db: Optional[AsyncSession] = None,
        redis_client: Optional[aioredis.Redis] = None
    ):
        self.graphs = {}
        self.db = db
        self.pgvector_db = pgvector_db
        self.redis = redis_client

    def _get_connected_auxiliary_nodes(self, agent_config: dict, llm_agent_id: str) -> Dict[str, Any]:
        """Get auxiliary nodes connected FROM LLM_AGENT (memory, tools, rag)."""
        nodes = agent_config.get("nodes", [])
        edges = agent_config.get("edges", [])

        # Find edges that originate FROM the LLM_AGENT node
        connected = {
            "memory": None,
            "tools": [],
            "rag": None
        }

        for edge in edges:
            target = edge.get("target")
            source = edge.get("source")

            # Check if this edge starts from the LLM_AGENT
            if source == llm_agent_id:
                # Find the target node
                target_node = next((n for n in nodes if n.get("id") == target), None)
                if target_node:
                    node_type = target_node.get("data", {}).get("type")

                    if node_type == "MEMORY":
                        connected["memory"] = target_node
                    elif node_type == "TOOL":
                        connected["tools"].append(target_node)
                    elif node_type == "RAG_RETRIEVER":
                        connected["rag"] = target_node

        return connected

    def build_graph_from_config(self, agent_config: dict) -> StateGraph:
        """Build a LangGraph workflow from agent configuration (Hub-and-Spoke pattern)."""

        # Create graph
        workflow = StateGraph(AgentState)

        # Add nodes from config - only main flow nodes (INPUT, LLM_AGENT, OUTPUT, DECISION, SUBGRAPH)
        nodes = agent_config.get("nodes", [])
        edges = agent_config.get("edges", [])

        # Auxiliary node types (don't add to workflow, queried by LLM_AGENT)
        auxiliary_types = {"MEMORY", "TOOL", "RAG_RETRIEVER"}

        # Register node handlers (only for main flow nodes)
        for node in nodes:
            node_type = node.get("data", {}).get("type")
            node_id = node.get("id")

            # Skip auxiliary nodes - they're queried, not executed
            if node_type in auxiliary_types:
                continue

            if node_type == "INPUT":
                workflow.add_node(node_id, self._handle_input_node)
            elif node_type == "LLM_AGENT":
                workflow.add_node(node_id, self._handle_llm_agent_node)
            elif node_type == "DECISION":
                workflow.add_node(node_id, self._handle_decision_node)
            elif node_type == "OUTPUT":
                workflow.add_node(node_id, self._handle_output_node)
            elif node_type == "SUBGRAPH":
                workflow.add_node(node_id, self._handle_subgraph_node)
            elif node_type == "FILE_READER":
                workflow.add_node(node_id, self._handle_file_reader_node)

        # Add edges - only for main flow (skip edges to auxiliary nodes)
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")

            # Check if target is an auxiliary node
            target_node = next((n for n in nodes if n.get("id") == target), None)
            if target_node:
                target_type = target_node.get("data", {}).get("type")
                # Skip edges to auxiliary nodes (they're queried, not in flow)
                if target_type in auxiliary_types:
                    continue

            workflow.add_edge(source, target)

        # Set entry point (find INPUT node)
        input_node = next((n for n in nodes if n.get("data", {}).get("type") == "INPUT"), None)
        if input_node:
            workflow.set_entry_point(input_node["id"])

        # Find output node and connect to END
        output_node = next((n for n in nodes if n.get("data", {}).get("type") == "OUTPUT"), None)
        if output_node:
            workflow.add_edge(output_node["id"], END)

        return workflow.compile()

    def _get_node_config(self, state: AgentState, node_type: str) -> Dict:
        """Get configuration for a specific node type from agent config."""
        nodes = state["agent_config"].get("nodes", [])
        node = next((n for n in nodes if n.get("data", {}).get("type") == node_type), None)
        if node:
            return node.get("data", {}).get("config", {})
        return {}

    def _handle_input_node(self, state: AgentState) -> AgentState:
        """Handle INPUT node - initialize agent state with mode support."""
        start_time = datetime.utcnow()

        # Get node info for tracking
        nodes = state["agent_config"].get("nodes", [])
        current_node = next((n for n in nodes if n.get("data", {}).get("type") == "INPUT"), None)
        node_id = current_node.get("id", "input-unknown") if current_node else "input-unknown"
        node_label = current_node.get("data", {}).get("label", "Input Node") if current_node else "Input Node"

        # Get node configuration
        node_config = self._get_node_config(state, "INPUT")
        mode = node_config.get("mode", "chat")

        # Get raw input from state
        raw_input = state.get("raw_input", "")

        # Capture input snapshot
        input_snapshot = {
            "raw_input": raw_input if isinstance(raw_input, (str, dict, list, int, float, bool)) else str(raw_input),
            "mode": mode,
        }

        # Process based on mode
        try:
            if mode == "chat":
                processed_input = self._process_chat_input(raw_input, node_config)
            elif mode == "json":
                processed_input = self._process_json_input(raw_input, node_config)
            elif mode == "form":
                processed_input = self._process_form_input(raw_input, node_config)
            else:
                # Default to chat mode for unknown modes
                processed_input = self._process_chat_input(raw_input, node_config)

            # Store processed input in state
            state["processed_input"] = processed_input
            state["input_metadata"] = {
                "mode": mode,
                "timestamp": datetime.utcnow().isoformat(),
                "validation_passed": True,
            }

            # Convert to message format for LangGraph
            if mode == "chat":
                message_content = processed_input.get("message", str(raw_input))
            else:
                message_content = json.dumps(processed_input, indent=2)

            # Add message to state
            state["messages"] = [HumanMessage(content=message_content)]

            # Capture output snapshot
            output_snapshot = {
                "processed_input": processed_input,
                "validation_passed": True,
                "mode": mode,
            }

            # Store node output for templating (other nodes can reference this)
            state["node_outputs"][node_id] = processed_input

            # Calculate duration
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Add execution trace
            state["execution_trace"].append({
                "node_id": node_id,
                "node_type": "INPUT",
                "node_label": node_label,
                "input_data": input_snapshot,
                "output_data": output_snapshot,
                "timestamp": start_time.isoformat(),
                "duration_ms": duration_ms,
                "status": "success",
                "error": None,
                "metadata": state["input_metadata"],
            })

        except ValueError as e:
            # Validation failed
            state["input_metadata"] = {
                "mode": mode,
                "timestamp": datetime.utcnow().isoformat(),
                "validation_passed": False,
                "error": str(e),
            }
            # Add error message
            state["messages"] = [HumanMessage(content=f"Input validation error: {str(e)}")]

            # Calculate duration
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Add error trace
            state["execution_trace"].append({
                "node_id": node_id,
                "node_type": "INPUT",
                "node_label": node_label,
                "input_data": input_snapshot,
                "output_data": None,
                "timestamp": start_time.isoformat(),
                "duration_ms": duration_ms,
                "status": "error",
                "error": str(e),
                "metadata": state["input_metadata"],
            })

        state["execution_path"].append("INPUT")
        return state

    def _process_chat_input(self, raw_input: Any, config: Dict) -> Dict:
        """Process chat mode input."""
        chat_config = config.get("chatConfig", {})

        result = {
            "message": str(raw_input),
            "mode": "chat",
        }

        # Add system message if configured
        system_msg = chat_config.get("systemMessage")
        if system_msg:
            result["system_message"] = system_msg

        # Add metadata if configured
        metadata_config = chat_config.get("metadata", {})
        if metadata_config:
            result["metadata"] = {}
            if metadata_config.get("collectTimestamp", False):
                result["metadata"]["timestamp"] = datetime.utcnow().isoformat()
            if metadata_config.get("collectUserId", False):
                result["metadata"]["user_id"] = metadata_config.get("userId", "unknown")

        return result

    def _process_json_input(self, raw_input: Any, config: Dict) -> Dict:
        """Process and validate JSON mode input."""
        json_config = config.get("jsonConfig", {})
        schema = json_config.get("schema")

        # Parse input if string
        if isinstance(raw_input, str):
            try:
                data = json.loads(raw_input)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON input: {str(e)}")
        elif isinstance(raw_input, dict):
            data = raw_input
        else:
            raise ValueError(f"JSON mode expects string or dict, got {type(raw_input)}")

        # Validate against schema if provided
        if schema and json_config.get("validateOnInput", True):
            try:
                json_validate(instance=data, schema=schema)
            except JsonValidationError as e:
                raise ValueError(f"JSON validation failed: {e.message}")

        # Apply defaults from schema
        if schema and "properties" in schema:
            for key, prop_schema in schema["properties"].items():
                if key not in data and "default" in prop_schema:
                    data[key] = prop_schema["default"]

        return data

    def _process_form_input(self, raw_input: Any, config: Dict) -> Dict:
        """Process and validate form mode input."""
        form_config = config.get("formConfig", {})
        fields = form_config.get("fields", [])

        # Parse input
        if isinstance(raw_input, str):
            try:
                data = json.loads(raw_input)
            except json.JSONDecodeError:
                raise ValueError("Form input must be valid JSON or dict")
        elif isinstance(raw_input, dict):
            data = raw_input
        else:
            raise ValueError(f"Form mode expects string or dict, got {type(raw_input)}")

        result = {}
        errors = []

        # Validate each field
        for field in fields:
            key = field.get("key")
            if not key:
                continue

            value = data.get(key)

            # Check required
            if field.get("required", False) and value is None:
                errors.append(f"Field '{key}' is required")
                continue

            # Apply default
            if value is None and "default" in field:
                value = field["default"]

            # Type validation and conversion
            if value is not None:
                field_type = field.get("type", "text")

                if field_type == "number":
                    try:
                        value = float(value) if isinstance(value, (int, float, str)) else value
                    except (ValueError, TypeError):
                        errors.append(f"Field '{key}' must be a number")
                        continue

                # Validation rules
                validation = field.get("validation", {})
                if validation:
                    if "min" in validation and isinstance(value, (int, float)):
                        if value < validation["min"]:
                            msg = validation.get("customMessage", f"Field '{key}' must be >= {validation['min']}")
                            errors.append(msg)
                    if "max" in validation and isinstance(value, (int, float)):
                        if value > validation["max"]:
                            msg = validation.get("customMessage", f"Field '{key}' must be <= {validation['max']}")
                            errors.append(msg)
                    if "minLength" in validation and isinstance(value, str):
                        if len(value) < validation["minLength"]:
                            errors.append(f"Field '{key}' must be at least {validation['minLength']} characters")
                    if "maxLength" in validation and isinstance(value, str):
                        if len(value) > validation["maxLength"]:
                            errors.append(f"Field '{key}' must be at most {validation['maxLength']} characters")
                    if "pattern" in validation and isinstance(value, str):
                        import re
                        if not re.match(validation["pattern"], value):
                            msg = validation.get("customMessage", f"Field '{key}' does not match required pattern")
                            errors.append(msg)

            result[key] = value

        if errors:
            raise ValueError(f"Form validation failed: {'; '.join(errors)}")

        return result

    async def _handle_memory_node(self, state: AgentState) -> AgentState:
        """Handle MEMORY node - load and manage conversation history."""
        state["execution_path"].append("MEMORY")

        # Get memory node configuration
        node_config = self._get_node_config(state, "MEMORY")

        if not self.redis:
            # No Redis client, skip memory loading
            state["chat_history"] = []
            state["session_id"] = None
            return state

        # Create memory manager
        memory_manager = MemoryManager(self.redis)

        # Get or generate session ID
        session_id = state.get("session_id")
        if not session_id:
            # Try to get from processed input
            session_id = state.get("processed_input", {}).get("session_id")

        if not session_id:
            # Try to get from raw input metadata
            if isinstance(state.get("raw_input"), dict):
                session_id = state["raw_input"].get("session_id")

        # Get current user input for context
        current_input = ""
        if state.get("messages"):
            current_input = state["messages"][-1].content if state["messages"] else ""

        # Load memory context
        memory_context = await memory_manager.get_memory_context(
            session_id=session_id,
            config=node_config,
            current_input=current_input
        )

        # Store in state
        state["chat_history"] = memory_context.get("chat_history", [])
        state["session_id"] = memory_context.get("session_id")
        state["memory_context"] = {
            "memory_type": memory_context.get("memory_type"),
            "message_count": len(memory_context.get("chat_history", []))
        }

        return state

    async def _handle_llm_agent_node(self, state: AgentState) -> AgentState:
        """Handle LLM_AGENT node - process with language model (Hub-and-Spoke pattern)."""
        start_time = datetime.utcnow()

        # Get node configuration
        nodes = state["agent_config"].get("nodes", [])
        llm_agent_node = next((n for n in nodes if n.get("data", {}).get("type") == "LLM_AGENT"), None)
        if not llm_agent_node:
            raise ValueError("LLM_AGENT node not found in configuration")

        llm_agent_id = llm_agent_node.get("id")
        node_label = llm_agent_node.get("data", {}).get("label", "LLM Agent")
        node_config = llm_agent_node.get("data", {}).get("config", {})

        # Build template context from previous node outputs
        context = state.get("node_outputs", {})

        # Capture input snapshot
        input_snapshot = {
            "messages": [msg.content for msg in state.get("messages", [])],
            "system_prompt_template": node_config.get("systemPrompt", ""),
            "model_config": node_config.get("modelConfig", {}),
            "context_available": list(context.keys()),
        }

        try:
            # Resolve templates in system prompt
            system_prompt = node_config.get("systemPrompt", "")
            if system_prompt and "{{" in system_prompt:
                system_prompt = template_engine.resolve_template(system_prompt, context)
                node_config = {**node_config, "systemPrompt": system_prompt}
                input_snapshot["system_prompt_resolved"] = system_prompt

            # STEP 1: Query connected auxiliary nodes
            connected = self._get_connected_auxiliary_nodes(state["agent_config"], llm_agent_id)

            # Query MEMORY node if connected
            if connected["memory"]:
                memory_config = connected["memory"].get("data", {}).get("config", {})

                if self.redis:
                    memory_manager = MemoryManager(self.redis)

                    # Get or extract session ID
                    session_id = state.get("session_id")
                    if not session_id:
                        session_id = state.get("processed_input", {}).get("session_id")
                    if not session_id and isinstance(state.get("raw_input"), dict):
                        session_id = state["raw_input"].get("session_id")

                    # Get current input
                    current_input = ""
                    if state.get("messages"):
                        current_input = state["messages"][-1].content if state["messages"] else ""

                    # Load memory context
                    memory_context = await memory_manager.get_memory_context(
                        session_id=session_id,
                        config=memory_config,
                        current_input=current_input
                    )

                    state["chat_history"] = memory_context.get("chat_history", [])
                    state["session_id"] = memory_context.get("session_id")
                    state["memory_context"] = {
                        "memory_type": memory_context.get("memory_type"),
                        "message_count": len(memory_context.get("chat_history", []))
                    }

            # Query TOOL nodes if connected and fetch from database
            available_tools = []
            langchain_tools = []
            if connected["tools"] and self.db:
                for tool_node in connected["tools"]:
                    tool_config = tool_node.get("data", {}).get("config", {})
                    tool_id = tool_config.get("toolId")
                    if tool_id:
                        try:
                            # Fetch tool from database
                            tool_uuid = UUID(tool_id) if isinstance(tool_id, str) else tool_id
                            db_tool = await self.db.get(Tool, tool_uuid)

                            if db_tool:
                                available_tools.append(tool_id)
                                # Convert to LangChain tool
                                langchain_tool = ToolConverter.convert_to_langchain_tool(db_tool)
                                langchain_tools.append(langchain_tool)
                        except Exception as e:
                            # Log error but continue with other tools
                            print(f"Error loading tool {tool_id}: {str(e)}")

            # Query RAG node if connected
            rag_context = None
            rag_chunks = []
            if connected["rag"] and self.pgvector_db:
                rag_config = connected["rag"].get("data", {}).get("config", {})

                try:
                    # Get current user query
                    current_query = state["messages"][-1].content if state["messages"] else ""

                    # Get collection configuration
                    collection_id = rag_config.get("collectionId")
                    credential_id = rag_config.get("credentialId")

                    # Get API key from credential if provided
                    api_key = None
                    if credential_id and self.db:
                        credential = await self.db.get(Credential, UUID(credential_id) if isinstance(credential_id, str) else credential_id)
                        if credential:
                            api_key = credential.api_key

                    if collection_id:
                        # Initialize RAG service with collection's embedding config
                        rag_service_temp = RAGService(self.pgvector_db)
                        collection = await rag_service_temp.get_collection_by_id(collection_id)

                        if collection:
                            # Create RAG service with collection's embedding model and API key
                            rag_service = RAGService.create_from_collection(
                                self.pgvector_db,
                                collection,
                                api_key=api_key
                            )

                            # Retrieve relevant chunks
                            rag_chunks = await rag_service.retrieve_relevant_chunks(
                                query=current_query,
                                collection_id=collection_id,
                                top_k=rag_config.get("topK", 5),
                                score_threshold=rag_config.get("scoreThreshold", 0.7),
                                search_method=rag_config.get("searchMethod", "cosine")
                            )

                            # Format context for LLM
                            if rag_chunks:
                                rag_context = await rag_service.format_rag_context(
                                    rag_chunks,
                                    include_metadata=rag_config.get("includeMetadata", True)
                                )

                                avg_score = sum(c['score'] for c in rag_chunks) / len(rag_chunks)
                                print(f"RAG retrieved {len(rag_chunks)} chunks with avg score: {avg_score:.3f}")

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
    
            # 3. Inject conversation history from memory (if loaded)
            if chat_history := state.get("chat_history"):
                messages.extend(chat_history)
    
            # 4. Add current messages from state
            messages.extend(state["messages"])
    
            # 3. Get credential and create LLM client
            credential_id = node_config.get("credentialId")
            if not credential_id:
                raise ValueError("LLM_AGENT node requires a credentialId")
    
            if not self.db:
                raise ValueError("Database session is required for LLM execution")
    
            # Fetch credential from database
            credential = await self.db.get(Credential, credential_id)
            if not credential:
                raise ValueError(f"Credential not found: {credential_id}")
    
            # Create LLM client
            model_config = node_config.get("modelConfig", {})
            try:
                llm_client = LLMClient.create_client(credential, model_config)
            except Exception as e:
                raise ValueError(f"Failed to create LLM client: {str(e)}")
    
            # 4. Invoke LLM with tools (if available)
            try:
                # Bind tools to LLM if available
                if langchain_tools:
                    response = await LLMClient.invoke(llm_client, messages, tools=langchain_tools)
                else:
                    response = await LLMClient.invoke(llm_client, messages)
    
                # Extract token usage
                usage = LLMClient.extract_usage(response)
    
                # Store usage in state for tracking
                if "llm_usage" not in state:
                    state["llm_usage"] = {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0
                    }
    
                state["llm_usage"]["prompt_tokens"] += usage["prompt_tokens"]
                state["llm_usage"]["completion_tokens"] += usage["completion_tokens"]
                state["llm_usage"]["total_tokens"] += usage["total_tokens"]
    
                # Calculate cost
                cost = LLMClient.calculate_cost(
                    usage,
                    model_config.get("model", ""),
                    credential.provider
                )
                if "llm_cost" not in state:
                    state["llm_cost"] = 0.0
                state["llm_cost"] += cost
    
                # Add response to messages
                state["messages"].append(response)
    
                # Update memory if session exists and memory node is connected
                if session_id := state.get("session_id"):
                    if self.redis and connected["memory"]:
                        memory_manager = MemoryManager(self.redis)
                        memory_config = connected["memory"].get("data", {}).get("config", {})
    
                        # Get the user message (last message in state before LLM response)
                        user_message = state["messages"][-2] if len(state["messages"]) >= 2 else None
    
                        if user_message and memory_config:
                            await memory_manager.update_memory(
                                session_id=session_id,
                                user_message=user_message,
                                ai_message=response,
                                existing_history=state.get("chat_history", []),
                                config=memory_config
                            )
    
                # Capture output snapshot
                output_snapshot = {
                    "response": response.content if hasattr(response, 'content') else str(response),
                    "tokens_used": state.get("llm_usage", {}),
                    "cost": state.get("llm_cost", 0.0),
                    "tools_available": [tool.name for tool in langchain_tools] if langchain_tools else [],
                    "memory_loaded": bool(state.get("chat_history")),
                    "rag_chunks_count": len(rag_chunks) if rag_chunks else 0,
                }
    
                # Store node output for templating
                state["node_outputs"][llm_agent_id] = {
                    "response": response.content if hasattr(response, 'content') else str(response),
                    "tokens": state.get("llm_usage", {}),
                    "cost": state.get("llm_cost", 0.0),
                }
    
                # Calculate duration
                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
    
                # Add execution trace
                state["execution_trace"].append({
                    "node_id": llm_agent_id,
                    "node_type": "LLM_AGENT",
                    "node_label": node_label,
                    "input_data": input_snapshot,
                    "output_data": output_snapshot,
                    "timestamp": start_time.isoformat(),
                    "duration_ms": duration_ms,
                    "status": "success",
                    "error": None,
                    "metadata": {
                        "model": model_config.get("model", ""),
                        "provider": credential.provider if 'credential' in locals() else "unknown",
                        "tokens_total": state.get("llm_usage", {}).get("total_tokens", 0),
                    },
                })
    
            except Exception as e:
                # Add error message to state
                error_msg = f"LLM execution error: {str(e)}"
                state["messages"].append(AIMessage(content=error_msg))
    
                # Calculate duration
                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
    
                # Add error trace
                state["execution_trace"].append({
                    "node_id": llm_agent_id,
                    "node_type": "LLM_AGENT",
                    "node_label": node_label,
                    "input_data": input_snapshot,
                    "output_data": None,
                    "timestamp": start_time.isoformat(),
                    "duration_ms": duration_ms,
                    "status": "error",
                    "error": str(e),
                    "metadata": None,
                })

                raise

        except Exception as e:
            # Add error message to state
            error_msg = f"LLM execution error: {str(e)}"
            state["messages"].append(AIMessage(content=error_msg))

            # Calculate duration
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Add error trace
            state["execution_trace"].append({
                "node_id": llm_agent_id,
                "node_type": "LLM_AGENT",
                "node_label": node_label,
                "input_data": input_snapshot,
                "output_data": None,
                "timestamp": start_time.isoformat(),
                "duration_ms": duration_ms,
                "status": "error",
                "error": str(e),
                "metadata": None,
            })

            raise

        state["execution_path"].append("LLM_AGENT")
        return state

    def _handle_rag_retriever_node(self, state: AgentState) -> AgentState:
        """Handle RAG_RETRIEVER node - retrieve from knowledge base."""
        state["execution_path"].append("RAG_RETRIEVER")

        # In production, this would query the RAG system
        # For now, return mock retrieval
        state["tool_results"]["rag_retrieval"] = {
            "documents": [],
            "scores": [],
        }

        return state

    def _handle_decision_node(self, state: AgentState) -> AgentState:
        """Handle DECISION node - conditional routing."""
        state["execution_path"].append("DECISION")

        # Evaluate decision condition
        # In production, this would evaluate the condition logic

        return state

    def _handle_tool_node(self, state: AgentState) -> AgentState:
        """Handle TOOL node - execute tool."""
        state["execution_path"].append("TOOL")

        # In production, this would execute the actual tool
        # For now, return mock result

        return state

    def _handle_output_node(self, state: AgentState) -> AgentState:
        """Handle OUTPUT node - format final response with template support."""
        start_time = datetime.utcnow()

        # Get node info for tracking
        nodes = state["agent_config"].get("nodes", [])
        output_node = next((n for n in nodes if n.get("data", {}).get("type") == "OUTPUT"), None)
        node_id = output_node.get("id", "output-unknown") if output_node else "output-unknown"
        node_label = output_node.get("data", {}).get("label", "Output Node") if output_node else "Output Node"
        node_config = output_node.get("data", {}).get("config", {}) if output_node else {}

        # Build template context from previous node outputs
        context = state.get("node_outputs", {})

        # Capture input snapshot
        input_snapshot = {
            "messages": [msg.content for msg in state.get("messages", [])],
            "template": node_config.get("template", ""),
            "format": node_config.get("format", "text"),
        }

        try:
            # Check if there's a custom output template
            output_template = node_config.get("template")

            if output_template and "{{" in output_template:
                # Resolve template using node outputs
                final_output = template_engine.resolve_template(output_template, context)
                input_snapshot["template_resolved"] = final_output
            elif state["messages"]:
                # Default: use last message content
                last_message = state["messages"][-1]
                final_output = last_message.content
            else:
                final_output = "No output generated"

            state["final_output"] = final_output

            # Capture output snapshot
            output_snapshot = {
                "final_output": final_output,
                "format": node_config.get("format", "text"),
                "length": len(final_output) if final_output else 0,
            }

            # Store node output for potential chaining
            state["node_outputs"][node_id] = {
                "output": final_output
            }

            # Calculate duration
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Add execution trace
            state["execution_trace"].append({
                "node_id": node_id,
                "node_type": "OUTPUT",
                "node_label": node_label,
                "input_data": input_snapshot,
                "output_data": output_snapshot,
                "timestamp": start_time.isoformat(),
                "duration_ms": duration_ms,
                "status": "success",
                "error": None,
                "metadata": node_config,
            })

        except Exception as e:
            # Calculate duration
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Add error trace
            state["execution_trace"].append({
                "node_id": node_id,
                "node_type": "OUTPUT",
                "node_label": node_label,
                "input_data": input_snapshot,
                "output_data": None,
                "timestamp": start_time.isoformat(),
                "duration_ms": duration_ms,
                "status": "error",
                "error": str(e),
                "metadata": None,
            })

            # Set error output
            state["final_output"] = f"Output formatting error: {str(e)}"

        state["execution_path"].append("OUTPUT")
        return state

    def _handle_subgraph_node(self, state: AgentState) -> AgentState:
        """Handle SUBGRAPH node - nested workflow."""
        state["execution_path"].append("SUBGRAPH")
        return state

    async def _handle_file_reader_node(self, state: AgentState) -> AgentState:
        """Handle FILE_READER node - read files from disk"""
        from app.services.file_reader import file_reader_service, FileReaderError
        from app.services.template_engine import NodeTemplateEngine

        start_time = datetime.utcnow()
        node_id = state["current_node"]
        agent_config = state["agent_config"]

        # Find the FILE_READER node config
        file_reader_config = None
        node_label = "File Reader"
        for node in agent_config.get("nodes", []):
            if node["id"] == node_id and node["data"]["type"] == "FILE_READER":
                file_reader_config = node["data"].get("config", {})
                node_label = node["data"].get("label", "File Reader")
                break

        if not file_reader_config:
            raise ValueError(f"FILE_READER node {node_id} not found in config")

        # Extract configuration
        file_path = file_reader_config.get("filePath", "")
        operation = file_reader_config.get("operation", "read_text")
        encoding = file_reader_config.get("encoding", "utf-8")
        error_handling = file_reader_config.get("errorHandling", "fail")
        default_value = file_reader_config.get("defaultValue", "")
        output_var_name = file_reader_config.get("outputVarName", "file_content")

        # Resolve templates in file path
        template_engine = NodeTemplateEngine()
        context = state.get("node_outputs", {})
        if "{{" in file_path:
            file_path = template_engine.resolve_template(file_path, context)

        # Capture input
        input_snapshot = {
            "file_path": file_path,
            "operation": operation,
            "encoding": encoding,
        }

        try:
            # Execute file operation
            if operation == "read_text":
                result = await file_reader_service.read_text(file_path, encoding)
            elif operation == "read_binary":
                result = await file_reader_service.read_binary(file_path)
            elif operation == "read_json":
                validate_schema = file_reader_config.get("validateSchema", False)
                json_schema = file_reader_config.get("jsonSchema")
                result = await file_reader_service.read_json(
                    file_path, encoding, validate_schema, json_schema
                )
            elif operation == "read_csv":
                result = await file_reader_service.read_csv(
                    file_path=file_path,
                    encoding=encoding,
                    delimiter=file_reader_config.get("csvDelimiter", ","),
                    has_header=file_reader_config.get("csvHasHeader", True),
                    skip_empty_lines=file_reader_config.get("csvSkipEmpty", True),
                    trim_fields=file_reader_config.get("csvTrimFields", True),
                )
            elif operation == "read_lines":
                result = await file_reader_service.read_lines(
                    file_path=file_path,
                    encoding=encoding,
                    skip_empty_lines=file_reader_config.get("linesSkipEmpty", True),
                    trim_lines=file_reader_config.get("linesTrim", True),
                    start_line=file_reader_config.get("linesStart"),
                    end_line=file_reader_config.get("linesEnd"),
                )
            elif operation == "get_metadata":
                result = await file_reader_service.get_file_metadata(file_path)
            else:
                raise ValueError(f"Unknown operation: {operation}")

            result["success"] = True
            output_snapshot = result
            status = "success"
            error_msg = None

        except FileReaderError as e:
            # Handle file reader specific errors
            if error_handling == "fail":
                raise
            elif error_handling == "default_value":
                result = {output_var_name: default_value, "success": False, "error": str(e)}
            else:  # continue
                result = {output_var_name: None, "success": False, "error": str(e)}

            output_snapshot = result
            status = "error"
            error_msg = str(e)

        except Exception as e:
            if error_handling == "fail":
                raise
            result = {output_var_name: None, "success": False, "error": str(e)}
            output_snapshot = result
            status = "error"
            error_msg = str(e)

        # Store node output
        state["node_outputs"][node_id] = result

        # Add execution trace
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        state["execution_trace"].append({
            "node_id": node_id,
            "node_type": "FILE_READER",
            "node_label": node_label,
            "input_data": input_snapshot,
            "output_data": output_snapshot,
            "timestamp": start_time.isoformat(),
            "duration_ms": round(duration_ms, 2),
            "status": status,
            "error": error_msg,
        })

        # Determine next node
        next_node = self._get_next_node(state, node_id)
        state["current_node"] = next_node
        state["execution_path"].append("FILE_READER")

        return state

    async def _handle_structured_output_parser_node(self, state: AgentState) -> AgentState:
        """Handle STRUCTURED_OUTPUT_PARSER node - parse LLM output into structured format."""
        start_time = datetime.utcnow()
        node_id = state["current_node"]
        agent_config = state["agent_config"]

        # Find the STRUCTURED_OUTPUT_PARSER node config
        parser_config = None
        node_label = "Output Parser"
        for node in agent_config.get("nodes", []):
            if node["id"] == node_id and node["data"]["type"] == "STRUCTURED_OUTPUT_PARSER":
                parser_config = node["data"].get("config", {})
                node_label = node["data"].get("label", "Output Parser")
                break

        if not parser_config:
            raise ValueError(f"STRUCTURED_OUTPUT_PARSER node {node_id} not found in config")

        # Get LLM output from previous node or messages
        llm_output = ""
        if state.get("messages"):
            last_message = state["messages"][-1]
            llm_output = last_message.content if hasattr(last_message, 'content') else str(last_message)

        # Capture input snapshot
        input_snapshot = {
            "raw_output": llm_output[:500] if llm_output else "",  # First 500 chars
            "parser_type": parser_config.get("parserType", "json_schema"),
            "strategy": parser_config.get("strategy", "lenient"),
        }

        try:
            # Parse output
            parser = StructuredOutputParser(parser_config)
            result = parser.parse(llm_output)

            # Store parsed data in node outputs
            state["node_outputs"][node_id] = {
                "parsed_data": result["parsed_data"],
                "parsing_success": result["parsing_success"],
                "validation_errors": result["validation_errors"],
                "fields_extracted": result["fields_extracted"],
            }

            # Calculate duration
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Add execution trace
            state["execution_trace"].append({
                "node_id": node_id,
                "node_type": "STRUCTURED_OUTPUT_PARSER",
                "node_label": node_label,
                "input_data": input_snapshot,
                "output_data": {
                    "parsed_data": result["parsed_data"],
                    "success": result["parsing_success"],
                    "fields_count": len(result["fields_extracted"]),
                },
                "timestamp": start_time.isoformat(),
                "duration_ms": duration_ms,
                "status": "success" if result["parsing_success"] else "error",
                "error": None if result["parsing_success"] else str(result.get("validation_errors")),
                "metadata": parser_config,
            })

            state["execution_path"].append("STRUCTURED_OUTPUT_PARSER")

            # Log success
            logger.info(f"Successfully parsed output: {len(result['fields_extracted'])} fields extracted")

        except Exception as e:
            # Calculate duration
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Add error trace
            state["execution_trace"].append({
                "node_id": node_id,
                "node_type": "STRUCTURED_OUTPUT_PARSER",
                "node_label": node_label,
                "input_data": input_snapshot,
                "output_data": None,
                "timestamp": start_time.isoformat(),
                "duration_ms": duration_ms,
                "status": "error",
                "error": str(e),
                "metadata": parser_config,
            })

            # Handle based on error handling config
            error_handling = parser_config.get("errorHandling", "fail")
            if error_handling == "fail":
                raise
            elif error_handling == "pass_through":
                state["node_outputs"][node_id] = {
                    "parsed_data": {"raw_text": llm_output},
                    "parsing_success": False,
                    "validation_errors": [str(e)],
                    "fields_extracted": [],
                }
            else:
                state["node_outputs"][node_id] = {
                    "parsed_data": {},
                    "parsing_success": False,
                    "validation_errors": [str(e)],
                    "fields_extracted": [],
                }

            logger.error(f"Parsing failed: {str(e)}")

        return state

    async def execute_agent(self, agent_config: dict, user_input: Any, input_mode: Optional[str] = None) -> dict:
        """Execute an agent with given input.

        Args:
            agent_config: The agent workflow configuration
            user_input: The user input (string, dict, or any JSON-serializable type)
            input_mode: Optional mode override (if not specified, uses node config)

        Returns:
            dict: Execution result with output, execution_path, messages, etc.
        """

        # Build graph from config
        graph = self.build_graph_from_config(agent_config)

        # Initialize state
        initial_state: AgentState = {
            "messages": [],  # Will be populated by INPUT node
            "agent_config": agent_config,
            "current_node": "",
            "execution_path": [],
            "execution_trace": [],  # Initialize execution trace
            "node_outputs": {},  # Initialize node outputs for templating
            "tool_results": {},
            "final_output": None,
            "raw_input": user_input,
            "processed_input": None,
            "input_metadata": None,
            "llm_usage": None,
            "llm_cost": None,
            "chat_history": None,
            "session_id": None,
            "memory_context": None,
        }

        # Execute graph
        result = await graph.ainvoke(initial_state)

        return {
            "output": result.get("final_output"),
            "execution_path": result.get("execution_path"),
            "execution_trace": result.get("execution_trace", []),  # Include execution trace
            "node_outputs": result.get("node_outputs", {}),  # Include node outputs
            "messages": [{"role": m.type, "content": m.content} for m in result.get("messages", [])],
            "tool_results": result.get("tool_results"),
            "input_metadata": result.get("input_metadata"),
            "processed_input": result.get("processed_input"),
            "llm_usage": result.get("llm_usage"),
            "llm_cost": result.get("llm_cost"),
        }
