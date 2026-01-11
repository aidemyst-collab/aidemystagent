from typing import TypedDict, Annotated, Sequence, Optional, Any, Dict, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
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
from app.services.external_rag_service import ExternalRAGService
from app.services.template_engine import template_engine
from app.services.audio_transcription_service import AudioTranscriptionService
from app.services.text_to_speech_service import TextToSpeechService
from app.models.credential import Credential
from app.models.tool import Tool
import redis.asyncio as aioredis
from uuid import UUID, uuid4

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
    input_mode: Optional[str]  # Input mode override (chat, json, form, audio)
    # LLM usage tracking
    llm_usage: Optional[Dict[str, int]]
    llm_cost: Optional[float]
    # Memory/conversation history
    chat_history: Optional[List[BaseMessage]]
    session_id: Optional[str]
    memory_context: Optional[Dict]
    # Multi-tenant context
    organization_id: Optional[str]  # Organization ID for tenant isolation
    workflow_id: Optional[str]  # Workflow ID for session scoping
    # Audio input (from INPUT node for AUDIO_TO_TEXT)
    audio_input: Optional[Dict[str, Any]]  # Audio data for transcription
    # Audio output
    audio_data: Optional[str]  # Base64 encoded audio for TTS output
    audio_format: Optional[str]  # Audio format (mp3, wav, etc.)
    # Voice call context (for VOICE_INPUT/VOICE_OUTPUT nodes)
    caller_id: Optional[str]  # Caller phone number
    provider: Optional[str]  # Voice provider (twilio, etisalat)
    voice_output: Optional[Dict[str, Any]]  # Voice output response data
    output_audio: Optional[str]  # Base64 encoded output audio


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
            elif node_type == "AUDIO_TO_TEXT":
                workflow.add_node(node_id, self._handle_audio_to_text_node)
            elif node_type == "TEXT_TO_AUDIO":
                workflow.add_node(node_id, self._handle_text_to_audio_node)
            elif node_type == "CODE":
                workflow.add_node(node_id, self._handle_code_node)
            elif node_type == "VOICE_INPUT":
                workflow.add_node(node_id, self._handle_voice_input_node)
            elif node_type == "VOICE_OUTPUT":
                workflow.add_node(node_id, self._handle_voice_output_node)

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

        # Override mode if input_mode is specified in state
        if state.get("input_mode"):
            mode = state["input_mode"]

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
            elif mode == "audio":
                processed_input = self._process_audio_input(raw_input, node_config, state)
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
            elif mode == "audio":
                # For audio mode, use placeholder - actual text comes from AUDIO_TO_TEXT node
                # Do NOT include audio_data in message - it's too large!
                message_content = processed_input.get("message", "[Audio Input]")
                # Store audio data separately in state for AUDIO_TO_TEXT node
                state["audio_input"] = {
                    "audio_data": processed_input.get("audio_data"),
                    "audio_format": processed_input.get("audio_format"),
                    "output_format": processed_input.get("output_format"),
                    "sample_rate": processed_input.get("sample_rate"),
                    "source_provider": processed_input.get("source_provider"),
                }
            else:
                message_content = json.dumps(processed_input, indent=2)

            # Add message to state
            state["messages"] = [HumanMessage(content=message_content)]

            # Capture output snapshot (exclude large audio_data from trace)
            if mode == "audio":
                # For audio mode, don't include raw audio_data in output snapshot
                output_snapshot = {
                    "processed_input": {k: v for k, v in processed_input.items() if k != "audio_data"},
                    "validation_passed": True,
                    "mode": mode,
                    "audio_data_size": len(processed_input.get("audio_data", "")) if processed_input.get("audio_data") else 0,
                }
                # Store minimal output for templating (without audio_data)
                state["node_outputs"][node_id] = {
                    "message": processed_input.get("message"),
                    "mode": "audio",
                    "audio_format": processed_input.get("audio_format"),
                    "requires_transcription": True,
                }
            else:
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

    def _process_audio_input(self, raw_input: Any, config: Dict, state: AgentState) -> Dict:
        """Process audio mode input - receive and normalize audio (NO transcription).

        Transcription is handled by AUDIO_TO_TEXT node.

        Args:
            raw_input: Either a JSON string/dict with audio_data, or just the audio data
            config: Node configuration with audioConfig settings
            state: Agent state for accessing credentials

        Returns:
            Dict with normalized audio data for AUDIO_TO_TEXT node to consume
        """
        audio_config = config.get("audioConfig", {})

        # Parse input to extract audio data
        if isinstance(raw_input, str):
            try:
                data = json.loads(raw_input)
            except json.JSONDecodeError:
                # Assume it's base64 audio data directly
                data = {"audio_data": raw_input}
        elif isinstance(raw_input, dict):
            data = raw_input
        else:
            raise ValueError(f"Audio mode expects string or dict, got {type(raw_input)}")

        audio_data = data.get("audio_data")
        audio_format = data.get("audio_format", "webm")

        if not audio_data:
            raise ValueError("Audio input requires 'audio_data' field with base64 encoded audio")

        # Detect source provider
        source = audio_config.get("source", "microphone")
        twilio_config = audio_config.get("twilioConfig", {})

        # Normalize audio based on source
        normalized_format = audio_format
        if source == "twilio":
            # Twilio sends mulaw 8kHz - mark for conversion if needed
            normalized_format = twilio_config.get("format", "mulaw")
            sample_rate = twilio_config.get("sampleRate", 8000)
        else:
            sample_rate = data.get("sample_rate")

        # Output format preference (for AUDIO_TO_TEXT node)
        output_format = audio_config.get("outputFormat", normalized_format)

        # Return normalized audio data - NO transcription here
        # AUDIO_TO_TEXT node will handle transcription
        return {
            "message": "[Audio Input - Awaiting Transcription]",
            "mode": "audio",
            "audio_data": audio_data,
            "audio_format": normalized_format,
            "output_format": output_format,
            "sample_rate": sample_rate,
            "source_provider": source,
            "requires_transcription": True,  # Flag for AUDIO_TO_TEXT node
        }

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

        # Load memory context (with multi-tenant isolation)
        memory_context = await memory_manager.get_memory_context(
            session_id=session_id,
            config=node_config,
            current_input=current_input,
            organization_id=state.get("organization_id"),
            workflow_id=state.get("workflow_id")
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

                    # Load memory context (with multi-tenant isolation)
                    memory_context = await memory_manager.get_memory_context(
                        session_id=session_id,
                        config=memory_config,
                        current_input=current_input,
                        organization_id=state.get("organization_id"),
                        workflow_id=state.get("workflow_id")
                    )

                    state["chat_history"] = memory_context.get("chat_history", [])
                    state["session_id"] = memory_context.get("session_id")
                    state["memory_context"] = {
                        "memory_type": memory_context.get("memory_type"),
                        "message_count": len(memory_context.get("chat_history", []))
                    }

                    # Log memory details for debugging
                    chat_history = memory_context.get("chat_history", [])
                    input_snapshot["memory"] = {
                        "status": "loaded",
                        "session_id": session_id,
                        "memory_type": memory_config.get("type", "buffer"),
                        "config": {
                            "window_size": memory_config.get("windowSize"),
                            "persistence_enabled": memory_config.get("persistence", {}).get("enabled", False),
                        },
                        "messages_loaded": len(chat_history),
                        "history": [
                            {
                                "role": msg.type if hasattr(msg, 'type') else "unknown",
                                "content_preview": msg.content[:300] + "..." if len(msg.content) > 300 else msg.content,
                                "content_length": len(msg.content),
                            }
                            for msg in chat_history[-10:]  # Show last 10 messages
                        ],
                        "total_history_chars": sum(len(msg.content) for msg in chat_history),
                    }
                else:
                    input_snapshot["memory"] = {
                        "status": "not_loaded",
                        "reason": "Redis not available",
                    }
            else:
                input_snapshot["memory"] = {
                    "status": "not_connected",
                    "reason": "No MEMORY node connected to LLM_AGENT",
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
            if connected["rag"]:
                rag_config = connected["rag"].get("data", {}).get("config", {})
                rag_source = rag_config.get("ragSource", "internal")  # internal or external

                try:
                    # Get current user query
                    current_query = state["messages"][-1].content if state["messages"] else ""

                    if rag_source == "external":
                        # Use External DemystRAG
                        external_url = rag_config.get("externalUrl", "http://localhost:8003")
                        external_api_key = rag_config.get("externalApiKey")

                        if external_api_key:
                            rag_service = ExternalRAGService(
                                base_url=external_url,
                                api_key=external_api_key
                            )

                            # Retrieve relevant chunks from external RAG
                            rag_chunks = await rag_service.retrieve_relevant_chunks(
                                query=current_query,
                                collection_id=rag_config.get("collectionId"),
                                top_k=rag_config.get("topK", 5),
                                score_threshold=rag_config.get("scoreThreshold", 0.7)
                            )

                            # Format context for LLM
                            if rag_chunks:
                                rag_context = await rag_service.format_rag_context(
                                    rag_chunks,
                                    include_metadata=rag_config.get("includeMetadata", True)
                                )

                                avg_score = sum(c['score'] for c in rag_chunks) / len(rag_chunks)
                                print(f"External RAG retrieved {len(rag_chunks)} chunks with avg score: {avg_score:.3f}")
                        else:
                            print("External RAG configured but no API key provided")

                    elif self.pgvector_db:
                        # Use Internal pgvector RAG
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
                                    print(f"Internal RAG retrieved {len(rag_chunks)} chunks with avg score: {avg_score:.3f}")

                except Exception as e:
                    print(f"Error retrieving RAG context: {str(e)}")
                    rag_context = None
                    # Add RAG error to input snapshot
                    input_snapshot["rag_retrieval"] = {
                        "status": "error",
                        "error": str(e),
                    }

            # Add RAG details to input snapshot for debugging
            if connected["rag"]:
                rag_node_config = connected["rag"].get("data", {}).get("config", {})
                input_snapshot["rag_retrieval"] = {
                    "status": "success" if rag_chunks else "no_results",
                    "query": state["messages"][-1].content if state["messages"] else "",
                    "config": {
                        "rag_source": rag_node_config.get("ragSource", "internal"),
                        "collection_id": rag_node_config.get("collectionId"),
                        "top_k": rag_node_config.get("topK", 5),
                        "score_threshold": rag_node_config.get("scoreThreshold", 0.7),
                        "search_method": rag_node_config.get("searchMethod", "cosine"),
                    },
                    "results": {
                        "chunks_retrieved": len(rag_chunks) if rag_chunks else 0,
                        "chunks": [
                            {
                                "score": chunk.get("score", 0),
                                "content_preview": chunk.get("content", "")[:200] + "..." if len(chunk.get("content", "")) > 200 else chunk.get("content", ""),
                                "metadata": chunk.get("metadata", {}),
                            }
                            for chunk in (rag_chunks or [])[:5]  # Show max 5 chunks
                        ],
                        "context_chars": len(rag_context) if rag_context else 0,
                        "context_preview": rag_context[:500] + "..." if rag_context and len(rag_context) > 500 else rag_context,
                    }
                }

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
                # Calculate message stats for debugging
                total_chars = sum(len(m.content) for m in messages)
                estimated_tokens = total_chars // 4  # Rough estimate
                message_breakdown = []
                for i, msg in enumerate(messages):
                    msg_info = {
                        "index": i,
                        "type": type(msg).__name__.replace("Message", ""),
                        "chars": len(msg.content),
                        "estimated_tokens": len(msg.content) // 4,
                    }
                    # Include preview for large messages
                    if len(msg.content) > 200:
                        msg_info["preview"] = msg.content[:200] + "..."
                    else:
                        msg_info["content"] = msg.content
                    message_breakdown.append(msg_info)

                # Update input snapshot with message details
                input_snapshot["llm_request"] = {
                    "total_messages": len(messages),
                    "total_chars": total_chars,
                    "estimated_tokens": estimated_tokens,
                    "messages": message_breakdown,
                    "tools_count": len(langchain_tools) if langchain_tools else 0,
                }

                # Bind tools to LLM if available
                if langchain_tools:
                    response = await LLMClient.invoke(llm_client, messages, tools=langchain_tools)
                else:
                    response = await LLMClient.invoke(llm_client, messages)
    
                # Extract token usage
                usage = LLMClient.extract_usage(response)
    
                # Store usage in state for tracking
                if "llm_usage" not in state or state.get("llm_usage") is None:
                    state["llm_usage"] = {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0
                    }
    
                # Ensure usage is valid before updating
                if usage:
                    state["llm_usage"]["prompt_tokens"] += usage.get("prompt_tokens", 0)
                    state["llm_usage"]["completion_tokens"] += usage.get("completion_tokens", 0)
                    state["llm_usage"]["total_tokens"] += usage.get("total_tokens", 0)
    
                # Calculate cost (only if usage is available)
                if "llm_cost" not in state or state.get("llm_cost") is None:
                    state["llm_cost"] = 0.0
                if usage:
                    cost = LLMClient.calculate_cost(
                        usage,
                        model_config.get("model", ""),
                        credential.provider
                    )
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
                                config=memory_config,
                                organization_id=state.get("organization_id"),
                                workflow_id=state.get("workflow_id")
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

                # Set final output to error message and return gracefully
                state["final_output"] = error_msg
                state["execution_path"].append("LLM_AGENT")
                return state

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

            # Set final output to error message instead of raising
            # This allows the workflow to complete and return the execution trace
            state["final_output"] = error_msg
            state["execution_path"].append("LLM_AGENT")
            return state

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

            # Check if audio output is requested
            output_format = node_config.get("format", "text")
            audio_config = node_config.get("audioConfig", {})

            # Handle audio output - audio comes from TEXT_TO_AUDIO node
            if output_format == "audio":
                # Get audio from TEXT_TO_AUDIO node output or state
                audio_source_node_id = audio_config.get("audioSourceNodeId")

                # Try to get audio from specific node or find it in context
                audio_data = None
                audio_format_out = None
                audio_text = final_output  # Text transcript

                if audio_source_node_id and audio_source_node_id in context:
                    audio_source = context[audio_source_node_id]
                    audio_data = audio_source.get("audio_data")
                    audio_format_out = audio_source.get("audio_format")
                    audio_text = audio_source.get("text", final_output)
                elif state.get("audio_data"):
                    # Use audio from state (set by TEXT_TO_AUDIO node)
                    audio_data = state["audio_data"]
                    audio_format_out = state.get("audio_format", "mp3")
                else:
                    # Try to find TEXT_TO_AUDIO node output
                    for nid, output in context.items():
                        if isinstance(output, dict) and output.get("audio_data"):
                            audio_data = output["audio_data"]
                            audio_format_out = output.get("audio_format", "mp3")
                            audio_text = output.get("text", final_output)
                            break

                # Determine target provider
                target_provider = audio_config.get("targetProvider", "auto")

                # Auto-detect from INPUT node's source_provider
                if target_provider == "auto":
                    for nid, output in context.items():
                        if isinstance(output, dict) and output.get("source_provider"):
                            target_provider = output["source_provider"]
                            break
                    if target_provider == "auto":
                        target_provider = "browser"  # Default to browser

                # Store audio data in state
                if audio_data:
                    state["audio_data"] = audio_data
                    state["audio_format"] = audio_format_out

                # Generate provider-specific response
                twilio_response = None
                if target_provider == "twilio":
                    twilio_config = audio_config.get("twilioConfig", {})
                    response_type = twilio_config.get("responseType", "twiml_play")

                    if response_type == "twiml_say":
                        # Use Twilio's built-in TTS
                        say_voice = twilio_config.get("sayVoice", "alice")
                        say_language = twilio_config.get("sayLanguage", "en-US")
                        twilio_response = f'<Response><Say voice="{say_voice}" language="{say_language}">{audio_text}</Say></Response>'
                    else:
                        # Use custom audio with <Play>
                        play_url = twilio_config.get("playUrl", "")
                        if play_url:
                            twilio_response = f'<Response><Play>{play_url}</Play></Response>'
                        elif audio_data:
                            # Audio will be served via API endpoint
                            twilio_response = f'<Response><Play>{{audio_url}}</Play></Response>'

                    # Store TwiML response
                    state["twiml_response"] = twilio_response

                # Include transcript if configured
                include_transcript = audio_config.get("includeTranscript", True)
                if include_transcript:
                    state["audio_transcript"] = audio_text

            # Capture output snapshot
            output_snapshot = {
                "final_output": final_output,
                "format": output_format,
                "length": len(final_output) if final_output else 0,
                "has_audio": state.get("audio_data") is not None,
                "target_provider": audio_config.get("targetProvider", "browser") if output_format == "audio" else None,
            }

            # Store node output for potential chaining
            state["node_outputs"][node_id] = {
                "output": final_output,
                "audio_data": state.get("audio_data"),
                "audio_format": state.get("audio_format"),
                "twiml_response": state.get("twiml_response"),
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

    async def _handle_audio_to_text_node(self, state: AgentState) -> AgentState:
        """Handle AUDIO_TO_TEXT node - transcribe audio to text using various providers."""
        import base64

        start_time = datetime.utcnow()

        # Get node info for tracking
        nodes = state["agent_config"].get("nodes", [])
        audio_node = next((n for n in nodes if n.get("data", {}).get("type") == "AUDIO_TO_TEXT"), None)

        if not audio_node:
            raise ValueError("AUDIO_TO_TEXT node not found in configuration")

        node_id = audio_node.get("id", "audio-to-text-unknown")
        node_label = audio_node.get("data", {}).get("label", "Audio to Text")
        node_config = audio_node.get("data", {}).get("config", {})

        # Extract configuration
        audio_source = node_config.get("audioSource", "previous_node")  # 'previous_node', 'url', 'base64', 'twilio_stream'
        source_node_id = node_config.get("sourceNodeId")  # Reference to INPUT node
        source_field = node_config.get("sourceField", "audio_data")
        audio_url = node_config.get("audioUrl", "")
        audio_data = node_config.get("audioData", "")
        audio_format = node_config.get("audioFormat", "wav")
        sample_rate = node_config.get("sampleRate", 8000)
        twilio_format = node_config.get("twilioFormat", False)
        provider = node_config.get("provider", "openai_whisper")
        model = node_config.get("model")
        language = node_config.get("language")
        credential_id = node_config.get("credentialId")

        # Build template context and resolve templates
        context = state.get("node_outputs", {})

        # Handle 'previous_node' source - read audio from INPUT node output
        if audio_source == "previous_node":
            source_output = None

            # First, check if audio_input was stored directly in state (preferred method)
            if state.get("audio_input") and state["audio_input"].get("audio_data"):
                source_output = state["audio_input"]
                source_node_id = "audio_input"
                logger.info("AUDIO_TO_TEXT reading audio from state['audio_input']")
            # Second, try to find the source node (INPUT node) output in context
            elif source_node_id and source_node_id in context:
                source_output = context[source_node_id]
            else:
                # Auto-detect: find any node with audio_data (usually INPUT node)
                for nid, output in context.items():
                    if isinstance(output, dict) and output.get("audio_data"):
                        source_output = output
                        source_node_id = nid
                        break

            if not source_output:
                raise ValueError("AUDIO_TO_TEXT: No audio data found from previous node. Ensure INPUT node is configured for audio mode.")

            # Extract audio data from source node
            audio_data = source_output.get(source_field) or source_output.get("audio_data", "")
            audio_format = source_output.get("audio_format", "webm")
            sample_rate = source_output.get("sample_rate", 8000)

            # Check if source is Twilio
            source_provider = source_output.get("source_provider", "")
            if source_provider == "twilio":
                twilio_format = True

            logger.info(f"AUDIO_TO_TEXT reading audio from node: {source_node_id}, format: {audio_format}")

        # Resolve templates in audio URL if present
        if audio_url and "{{" in audio_url:
            from app.services.template_engine import template_engine
            audio_url = template_engine.resolve_template(audio_url, context)

        # Capture input snapshot
        input_snapshot = {
            "audio_source": audio_source,
            "audio_format": audio_format,
            "provider": provider,
            "model": model,
            "language": language,
            "sample_rate": sample_rate,
            "twilio_format": twilio_format,
        }

        if audio_source == "url":
            input_snapshot["audio_url"] = audio_url
        elif audio_source == "base64":
            input_snapshot["audio_data_length"] = len(audio_data) if audio_data else 0

        try:
            # Get credential for API key
            if not credential_id:
                raise ValueError("AUDIO_TO_TEXT node requires a credentialId for the transcription provider")

            if not self.db:
                raise ValueError("Database session is required for audio transcription")

            # Fetch credential from database
            credential = await self.db.get(Credential, credential_id)
            if not credential:
                raise ValueError(f"Credential not found: {credential_id}")

            api_key = credential.api_key

            # Perform transcription based on source
            if audio_source == "previous_node" and audio_data:
                # Transcribe audio from previous node (INPUT node)
                audio_bytes = base64.b64decode(audio_data)

                # Handle Twilio mulaw format
                if twilio_format:
                    actual_format = "mulaw"
                else:
                    actual_format = audio_format

                # Create service and transcribe
                service = AudioTranscriptionService(
                    provider=provider,
                    api_key=api_key,
                    model=model
                )
                result = await service.transcribe(
                    audio_data=audio_bytes,
                    audio_format=actual_format,
                    language=language,
                    sample_rate=sample_rate
                )

            elif audio_source == "url" and audio_url:
                # Transcribe from URL
                result = await AudioTranscriptionService.transcribe_from_url(
                    url=audio_url,
                    provider=provider,
                    api_key=api_key,
                    model=model,
                    language=language
                )

            elif audio_source == "base64" and audio_data:
                # Decode base64 audio
                audio_bytes = base64.b64decode(audio_data)

                # Handle Twilio mulaw format
                if twilio_format:
                    actual_format = "mulaw"
                else:
                    actual_format = audio_format

                # Create service and transcribe
                service = AudioTranscriptionService(
                    provider=provider,
                    api_key=api_key,
                    model=model
                )
                result = await service.transcribe(
                    audio_data=audio_bytes,
                    audio_format=actual_format,
                    language=language,
                    sample_rate=sample_rate
                )

            elif audio_source == "twilio_stream":
                # For Twilio media stream, audio data should already be collected
                # and passed as base64 mulaw
                if audio_data:
                    audio_bytes = base64.b64decode(audio_data)

                    service = AudioTranscriptionService(
                        provider=provider,
                        api_key=api_key,
                        model=model
                    )
                    result = await service.transcribe(
                        audio_data=audio_bytes,
                        audio_format="mulaw",
                        language=language,
                        sample_rate=8000  # Twilio uses 8kHz
                    )
                else:
                    raise ValueError("Twilio stream audio data not provided")

            else:
                raise ValueError(f"Invalid audio source: {audio_source}. Must be 'previous_node', 'url', 'base64', or 'twilio_stream'")

            # Capture output snapshot
            output_snapshot = {
                "success": result.get("success", False),
                "text": result.get("text", ""),
                "confidence": result.get("confidence"),
                "provider": result.get("provider", provider),
                "model": result.get("model", model),
                "error": result.get("error"),
            }

            # Store node output for templating
            state["node_outputs"][node_id] = {
                "text": result.get("text", ""),
                "confidence": result.get("confidence"),
                "success": result.get("success", False),
                "provider": result.get("provider", provider),
                "words": result.get("words", []),  # Some providers return word-level timing
            }

            # Also add transcribed text to messages for downstream LLM nodes
            if result.get("text"):
                # Append as a human message representing the transcribed speech
                state["messages"].append(HumanMessage(content=f"[Transcribed Audio]: {result.get('text')}"))

            # Calculate duration
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Add execution trace
            state["execution_trace"].append({
                "node_id": node_id,
                "node_type": "AUDIO_TO_TEXT",
                "node_label": node_label,
                "input_data": input_snapshot,
                "output_data": output_snapshot,
                "timestamp": start_time.isoformat(),
                "duration_ms": duration_ms,
                "status": "success" if result.get("success") else "error",
                "error": result.get("error"),
                "metadata": {
                    "provider": provider,
                    "model": model,
                    "text_length": len(result.get("text", "")),
                },
            })

            logger.info(f"Audio transcription completed: {len(result.get('text', ''))} characters transcribed")

        except Exception as e:
            # Calculate duration
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Capture error output
            output_snapshot = {
                "success": False,
                "text": "",
                "error": str(e),
            }

            # Store error in node outputs
            state["node_outputs"][node_id] = {
                "text": "",
                "success": False,
                "error": str(e),
            }

            # Add error trace
            state["execution_trace"].append({
                "node_id": node_id,
                "node_type": "AUDIO_TO_TEXT",
                "node_label": node_label,
                "input_data": input_snapshot,
                "output_data": output_snapshot,
                "timestamp": start_time.isoformat(),
                "duration_ms": duration_ms,
                "status": "error",
                "error": str(e),
                "metadata": None,
            })

            logger.error(f"Audio transcription failed: {str(e)}")
            raise

        state["execution_path"].append("AUDIO_TO_TEXT")
        return state

    async def _handle_text_to_audio_node(self, state: AgentState) -> AgentState:
        """Handle TEXT_TO_AUDIO node - convert text to speech using TTS providers."""

        start_time = datetime.utcnow()

        # Get node info for tracking
        nodes = state["agent_config"].get("nodes", [])
        tts_node = next((n for n in nodes if n.get("data", {}).get("type") == "TEXT_TO_AUDIO"), None)

        if not tts_node:
            raise ValueError("TEXT_TO_AUDIO node not found in configuration")

        node_id = tts_node.get("id", "text-to-audio-unknown")
        node_label = tts_node.get("data", {}).get("label", "Text to Audio")
        node_config = tts_node.get("data", {}).get("config", {})

        # Extract configuration
        text_source = node_config.get("textSource", "template")  # 'template', 'last_message', 'fixed'
        text_template = node_config.get("textTemplate", "")
        fixed_text = node_config.get("fixedText", "")
        provider = node_config.get("provider", "openai_tts")
        voice = node_config.get("voice")
        model = node_config.get("model")
        output_format = node_config.get("outputFormat", "mp3")
        speed = node_config.get("speed", 1.0)
        language = node_config.get("language")
        credential_id = node_config.get("credentialId")

        # Build template context
        context = state.get("node_outputs", {})

        # Determine text to synthesize
        if text_source == "template" and text_template:
            # Resolve template
            if "{{" in text_template:
                from app.services.template_engine import template_engine
                text_to_speak = template_engine.resolve_template(text_template, context)
            else:
                text_to_speak = text_template
        elif text_source == "last_message" and state.get("messages"):
            # Use last message content
            last_message = state["messages"][-1]
            text_to_speak = last_message.content if hasattr(last_message, 'content') else str(last_message)
        elif text_source == "fixed":
            text_to_speak = fixed_text
        else:
            # Default: try to use last message
            if state.get("messages"):
                last_message = state["messages"][-1]
                text_to_speak = last_message.content if hasattr(last_message, 'content') else str(last_message)
            else:
                text_to_speak = ""

        # Capture input snapshot
        input_snapshot = {
            "text_source": text_source,
            "text_length": len(text_to_speak),
            "text_preview": text_to_speak[:100] + "..." if len(text_to_speak) > 100 else text_to_speak,
            "provider": provider,
            "voice": voice,
            "output_format": output_format,
            "speed": speed,
        }

        try:
            if not text_to_speak:
                raise ValueError("No text provided for speech synthesis")

            # Get credential for API key
            if not credential_id:
                raise ValueError("TEXT_TO_AUDIO node requires a credentialId for the TTS provider")

            if not self.db:
                raise ValueError("Database session is required for text-to-speech")

            # Fetch credential from database
            credential = await self.db.get(Credential, credential_id)
            if not credential:
                raise ValueError(f"Credential not found: {credential_id}")

            api_key = credential.api_key

            # Create TTS service and synthesize
            service = TextToSpeechService(
                provider=provider,
                api_key=api_key,
                voice=voice,
                model=model
            )

            result = await service.synthesize(
                text=text_to_speak,
                output_format=output_format,
                speed=speed,
                language=language
            )

            # Capture output snapshot
            output_snapshot = {
                "success": result.get("success", False),
                "audio_format": result.get("audio_format", output_format),
                "provider": result.get("provider", provider),
                "voice": result.get("voice"),
                "model": result.get("model"),
                "text_length": result.get("text_length", 0),
                "audio_data_length": len(result.get("audio_data", "")),
                "error": result.get("error"),
            }

            # Store node output for templating
            state["node_outputs"][node_id] = {
                "audio_data": result.get("audio_data", ""),
                "audio_format": result.get("audio_format", output_format),
                "success": result.get("success", False),
                "provider": result.get("provider", provider),
                "voice": result.get("voice"),
                "text": text_to_speak,  # Include original text for transcript
                "text_length": len(text_to_speak),
            }

            # Also store in state for OUTPUT node to easily access
            state["audio_data"] = result.get("audio_data", "")
            state["audio_format"] = result.get("audio_format", output_format)

            # Calculate duration
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Add execution trace
            state["execution_trace"].append({
                "node_id": node_id,
                "node_type": "TEXT_TO_AUDIO",
                "node_label": node_label,
                "input_data": input_snapshot,
                "output_data": output_snapshot,
                "timestamp": start_time.isoformat(),
                "duration_ms": duration_ms,
                "status": "success" if result.get("success") else "error",
                "error": result.get("error"),
                "metadata": {
                    "provider": provider,
                    "voice": voice,
                    "format": output_format,
                },
            })

            logger.info(f"Text-to-speech completed: {len(text_to_speak)} chars -> {output_format} audio")

        except Exception as e:
            # Calculate duration
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Capture error output
            output_snapshot = {
                "success": False,
                "audio_data": "",
                "error": str(e),
            }

            # Store error in node outputs
            state["node_outputs"][node_id] = {
                "audio_data": "",
                "success": False,
                "error": str(e),
            }

            # Add error trace
            state["execution_trace"].append({
                "node_id": node_id,
                "node_type": "TEXT_TO_AUDIO",
                "node_label": node_label,
                "input_data": input_snapshot,
                "output_data": output_snapshot,
                "timestamp": start_time.isoformat(),
                "duration_ms": duration_ms,
                "status": "error",
                "error": str(e),
                "metadata": None,
            })

            logger.error(f"Text-to-speech failed: {str(e)}")
            raise

        state["execution_path"].append("TEXT_TO_AUDIO")
        return state

    async def _handle_code_node(self, state: AgentState) -> AgentState:
        """Handle CODE node - execute custom JavaScript or Python code."""
        import subprocess
        import tempfile
        import os

        start_time = datetime.utcnow()

        # Get node info for tracking
        nodes = state["agent_config"].get("nodes", [])
        code_node = next((n for n in nodes if n.get("data", {}).get("type") == "CODE"), None)

        if not code_node:
            raise ValueError("CODE node not found in configuration")

        node_id = code_node.get("id", "code-unknown")
        node_label = code_node.get("data", {}).get("label", "Code")
        node_config = code_node.get("data", {}).get("config", {})

        # Extract configuration
        language = node_config.get("language", "javascript")
        code = node_config.get("code", "")
        input_mapping = node_config.get("inputMapping", [])
        output_variable = node_config.get("outputVariable", "result")
        timeout = node_config.get("timeout", 30000) // 1000  # Convert ms to seconds
        sandboxed = node_config.get("sandboxed", True)

        # Build input data from upstream nodes
        context = state.get("node_outputs", {})
        input_data = {}

        for mapping in input_mapping:
            var_name = mapping.get("variableName")
            source_node_id = mapping.get("sourceNodeId")
            source_field = mapping.get("sourceField")

            if not var_name or not source_node_id:
                continue

            # Get data from source node
            source_output = context.get(source_node_id, {})

            if source_field:
                # Navigate to specific field (supports dot notation)
                value = source_output
                for part in source_field.split("."):
                    if isinstance(value, dict):
                        value = value.get(part, None)
                    else:
                        value = None
                        break
                input_data[var_name] = value
            else:
                # Use entire output
                input_data[var_name] = source_output

        # Capture input snapshot
        input_snapshot = {
            "language": language,
            "code_preview": code[:200] + "..." if len(code) > 200 else code,
            "code_length": len(code),
            "input_data": {k: str(v)[:100] for k, v in input_data.items()},  # Truncate for logging
            "timeout": timeout,
            "sandboxed": sandboxed,
        }

        try:
            # Execute code based on language
            if language == "javascript":
                result = await self._execute_javascript(code, input_data, timeout, sandboxed)
            elif language == "python":
                result = await self._execute_python(code, input_data, timeout, sandboxed)
            else:
                raise ValueError(f"Unsupported language: {language}")

            # Capture output snapshot
            output_snapshot = {
                "success": True,
                "result": result if isinstance(result, (dict, list, str, int, float, bool, type(None))) else str(result),
                "console_logs": result.get("__console_logs__", []) if isinstance(result, dict) else [],
            }

            # Clean up internal fields from result
            if isinstance(result, dict):
                result.pop("__console_logs__", None)

            # Store node output for templating
            state["node_outputs"][node_id] = {
                output_variable: result,
                "success": True,
            }

            # Calculate duration
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Add execution trace
            state["execution_trace"].append({
                "node_id": node_id,
                "node_type": "CODE",
                "node_label": node_label,
                "input_data": input_snapshot,
                "output_data": output_snapshot,
                "timestamp": start_time.isoformat(),
                "duration_ms": duration_ms,
                "status": "success",
                "error": None,
                "metadata": {
                    "language": language,
                    "sandboxed": sandboxed,
                },
            })

            logger.info(f"Code execution completed: {language}, {len(code)} chars, result type: {type(result).__name__}")

        except Exception as e:
            # Calculate duration
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Capture error output
            output_snapshot = {
                "success": False,
                "error": str(e),
            }

            # Store error in node outputs
            state["node_outputs"][node_id] = {
                output_variable: None,
                "success": False,
                "error": str(e),
            }

            # Add error trace
            state["execution_trace"].append({
                "node_id": node_id,
                "node_type": "CODE",
                "node_label": node_label,
                "input_data": input_snapshot,
                "output_data": output_snapshot,
                "timestamp": start_time.isoformat(),
                "duration_ms": duration_ms,
                "status": "error",
                "error": str(e),
                "metadata": None,
            })

            logger.error(f"Code execution failed: {str(e)}")
            raise

        state["execution_path"].append("CODE")
        return state

    async def _handle_voice_input_node(self, state: AgentState) -> AgentState:
        """Handle VOICE_INPUT node - receive audio from voice provider webhook.

        This node is triggered by voice webhooks (Twilio/Etisalat).
        The audio data is already in the state from the webhook handler.
        """
        start_time = datetime.utcnow()

        # Get node info for tracking
        nodes = state["agent_config"].get("nodes", [])
        voice_node = next((n for n in nodes if n.get("data", {}).get("type") == "VOICE_INPUT"), None)

        if not voice_node:
            raise ValueError("VOICE_INPUT node not found in configuration")

        node_id = voice_node.get("id", "voice-input-unknown")
        node_label = voice_node.get("data", {}).get("label", "Voice Input")
        node_config = voice_node.get("data", {}).get("config", {})

        context = state.get("context", {})
        input_snapshot = {
            "audio_data_present": bool(state.get("audio_data")),
            "caller_id": state.get("caller_id"),
            "session_id": state.get("session_id"),
            "provider": state.get("provider"),
        }

        try:
            # Audio data comes from webhook, already in state
            audio_data = state.get("audio_data")
            audio_format = state.get("audio_format", "mp3")
            caller_id = state.get("caller_id")
            session_id = state.get("session_id")
            provider = state.get("provider", node_config.get("provider", "twilio"))

            # Store voice input data in context for downstream nodes
            voice_input_output = {
                "audio_data": audio_data,
                "audio_format": audio_format,
                "caller_id": caller_id,
                "session_id": session_id,
                "provider": provider,
                "language": node_config.get("language", "en-US"),
            }

            context[node_id] = voice_input_output

            # Also set audio_input for AUDIO_TO_TEXT node
            state["audio_input"] = {
                "audio_data": audio_data,
                "audio_format": audio_format,
                "source_provider": provider,
            }

            state["context"] = context

            # Add execution trace
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            state["execution_trace"].append({
                "node_id": node_id,
                "node_type": "VOICE_INPUT",
                "node_label": node_label,
                "input_data": input_snapshot,
                "output_data": {
                    "audio_format": audio_format,
                    "provider": provider,
                    "caller_id": caller_id,
                },
                "duration_ms": duration_ms,
                "status": "success",
            })

            logger.info(f"VOICE_INPUT processed: provider={provider}, session={session_id}")

        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            state["execution_trace"].append({
                "node_id": node_id,
                "node_type": "VOICE_INPUT",
                "node_label": node_label,
                "input_data": input_snapshot,
                "output_data": None,
                "error": str(e),
                "duration_ms": duration_ms,
                "status": "error",
            })
            logger.error(f"VOICE_INPUT failed: {str(e)}")
            raise

        state["execution_path"].append("VOICE_INPUT")
        return state

    async def _handle_voice_output_node(self, state: AgentState) -> AgentState:
        """Handle VOICE_OUTPUT node - prepare audio response for voice provider.

        This node prepares the audio to be played back to the caller.
        The actual playback is handled by the voice webhook response.
        """
        start_time = datetime.utcnow()

        # Get node info for tracking
        nodes = state["agent_config"].get("nodes", [])
        voice_node = next((n for n in nodes if n.get("data", {}).get("type") == "VOICE_OUTPUT"), None)

        if not voice_node:
            raise ValueError("VOICE_OUTPUT node not found in configuration")

        node_id = voice_node.get("id", "voice-output-unknown")
        node_label = voice_node.get("data", {}).get("label", "Voice Output")
        node_config = voice_node.get("data", {}).get("config", {})

        context = state.get("context", {})
        input_snapshot = {"context_keys": list(context.keys())}

        try:
            # Get audio from previous node (TEXT_TO_AUDIO or direct audio)
            input_field = node_config.get("inputField", "audio_data")
            audio_data = None
            audio_format = node_config.get("audioFormat", "mp3")

            # Try to find audio in various places
            # 1. Check state directly
            if state.get(input_field):
                audio_data = state[input_field]
            # 2. Check context from TEXT_TO_AUDIO node
            elif state.get("audio_data"):
                audio_data = state["audio_data"]
                audio_format = state.get("audio_format", audio_format)
            # 3. Search context for audio output
            else:
                for nid, output in context.items():
                    if isinstance(output, dict) and output.get("audio_data"):
                        audio_data = output["audio_data"]
                        audio_format = output.get("audio_format", audio_format)
                        break

            after_action = node_config.get("afterResponse", "hangup")
            transfer_to = node_config.get("transferTo")
            fallback_message = node_config.get("fallbackMessage", "Sorry, I couldn't process that.")
            loop = node_config.get("loop", 1)

            # Prepare voice output response
            if audio_data:
                voice_output = {
                    "type": "audio",
                    "audio_data": audio_data,
                    "audio_format": audio_format,
                    "action": after_action,
                    "transfer_to": transfer_to,
                    "loop": loop,
                }
            else:
                # Fallback to text response
                voice_output = {
                    "type": "text",
                    "text": fallback_message,
                    "action": after_action,
                }

            # Store in state for webhook to pick up
            state["voice_output"] = voice_output
            context[node_id] = voice_output
            state["context"] = context

            # Also set output_audio for consistency
            if audio_data:
                state["output_audio"] = audio_data

            # Add execution trace
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            state["execution_trace"].append({
                "node_id": node_id,
                "node_type": "VOICE_OUTPUT",
                "node_label": node_label,
                "input_data": input_snapshot,
                "output_data": {
                    "type": voice_output["type"],
                    "action": voice_output["action"],
                    "has_audio": audio_data is not None,
                },
                "duration_ms": duration_ms,
                "status": "success",
            })

            logger.info(f"VOICE_OUTPUT prepared: type={voice_output['type']}, action={after_action}")

        except Exception as e:
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            state["execution_trace"].append({
                "node_id": node_id,
                "node_type": "VOICE_OUTPUT",
                "node_label": node_label,
                "input_data": input_snapshot,
                "output_data": None,
                "error": str(e),
                "duration_ms": duration_ms,
                "status": "error",
            })
            logger.error(f"VOICE_OUTPUT failed: {str(e)}")
            raise

        state["execution_path"].append("VOICE_OUTPUT")
        return state

    async def _execute_javascript(self, code: str, input_data: dict, timeout: int, sandboxed: bool) -> Any:
        """Execute JavaScript code using Node.js."""
        import subprocess
        import tempfile
        import os

        # Build the JavaScript wrapper
        wrapper_code = f"""
const input = {json.dumps(input_data)};
const __console_logs__ = [];
const originalLog = console.log;
console.log = (...args) => {{
    __console_logs__.push(args.map(a => typeof a === 'object' ? JSON.stringify(a) : String(a)).join(' '));
}};

try {{
    // User code
    const __userCode__ = async () => {{
        {code}
    }};

    (async () => {{
        const result = await __userCode__();
        console.log = originalLog;
        if (typeof result === 'object' && result !== null) {{
            result.__console_logs__ = __console_logs__;
            console.log(JSON.stringify(result));
        }} else {{
            console.log(JSON.stringify({{ result: result, __console_logs__: __console_logs__ }}));
        }}
    }})();
}} catch (e) {{
    console.error(JSON.stringify({{ error: e.message, __console_logs__: __console_logs__ }}));
    process.exit(1);
}}
"""

        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(wrapper_code)
            temp_file = f.name

        try:
            # Execute with Node.js
            result = subprocess.run(
                ['node', temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                try:
                    error_data = json.loads(error_msg)
                    raise ValueError(error_data.get("error", error_msg))
                except json.JSONDecodeError:
                    raise ValueError(error_msg)

            # Parse output
            output = result.stdout.strip()
            if output:
                try:
                    return json.loads(output)
                except json.JSONDecodeError:
                    return {"result": output}
            return {"result": None}

        finally:
            # Clean up temp file
            os.unlink(temp_file)

    async def _execute_python(self, code: str, input_data: dict, timeout: int, sandboxed: bool) -> Any:
        """Execute Python code in a subprocess."""
        import subprocess
        import tempfile
        import os

        # Build the Python wrapper
        wrapper_code = f'''
import json
import sys
from datetime import datetime

input = {json.dumps(input_data)}
__console_logs__ = []

class LogCapture:
    def __init__(self, original):
        self.original = original
    def write(self, msg):
        if msg.strip():
            __console_logs__.append(msg.strip())
        self.original.write(msg)
    def flush(self):
        self.original.flush()

sys.stdout = LogCapture(sys.stdout)

try:
    # User code
{chr(10).join("    " + line for line in code.split(chr(10)))}

    # Capture result
    if 'result' in dir():
        output = result
    else:
        output = None

    sys.stdout = sys.stdout.original
    if isinstance(output, dict):
        output["__console_logs__"] = __console_logs__
        print(json.dumps(output))
    else:
        print(json.dumps({{"result": output, "__console_logs__": __console_logs__}}))
except Exception as e:
    sys.stdout = sys.stdout.original
    print(json.dumps({{"error": str(e), "__console_logs__": __console_logs__}}), file=sys.stderr)
    sys.exit(1)
'''

        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(wrapper_code)
            temp_file = f.name

        try:
            # Execute with Python
            result = subprocess.run(
                ['python3', temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                try:
                    error_data = json.loads(error_msg)
                    raise ValueError(error_data.get("error", error_msg))
                except json.JSONDecodeError:
                    raise ValueError(error_msg)

            # Parse output
            output = result.stdout.strip()
            if output:
                try:
                    return json.loads(output)
                except json.JSONDecodeError:
                    return {"result": output}
            return {"result": None}

        finally:
            # Clean up temp file
            os.unlink(temp_file)

    async def execute_agent(
        self,
        agent_config: dict,
        user_input: Any,
        input_mode: Optional[str] = None,
        session_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        workflow_id: Optional[str] = None
    ) -> dict:
        """Execute an agent with given input.

        Args:
            agent_config: The agent workflow configuration
            user_input: The user input (string, dict, or any JSON-serializable type)
            input_mode: Optional mode override (if not specified, uses node config)
            session_id: Optional session ID for memory persistence (auto-generated if not provided)
            organization_id: Organization ID for multi-tenant session isolation
            workflow_id: Workflow/Agent ID for session scoping

        Returns:
            dict: Execution result with output, execution_path, messages, session_id, etc.
        """
        # Auto-generate session_id if not provided
        # This ensures sessions work in both playground (frontend provides) and API (auto-generated)
        if not session_id:
            session_id = MemoryManager.generate_session_id()
            logger.info(f"Auto-generated session_id: {session_id}")

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
            "input_mode": input_mode,  # Pass input mode to nodes
            "llm_usage": None,
            "llm_cost": None,
            "chat_history": None,
            "session_id": session_id,  # Session ID (provided or auto-generated)
            "memory_context": None,
            "organization_id": str(organization_id) if organization_id else None,
            "workflow_id": str(workflow_id) if workflow_id else None,
            "audio_input": None,  # Will be populated by INPUT node for audio mode
            "audio_data": None,  # Will be populated by TTS if configured
            "audio_format": None,
        }

        # Execute graph with error handling to capture partial execution trace
        try:
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
                "audio_data": result.get("audio_data"),  # Include audio output from TEXT_TO_AUDIO
                "audio_format": result.get("audio_format"),
                "twiml_response": result.get("twiml_response"),  # TwiML for Twilio
                "audio_transcript": result.get("audio_transcript"),  # Text transcript of audio
                # Session info for multi-turn conversations
                "session_id": session_id,  # Return session_id so caller can continue conversation
            }
        except Exception as e:
            # Return partial results with error information
            # The execution trace should contain error information up to the point of failure
            error_message = str(e)
            print(f"Workflow execution error: {error_message}")

            return {
                "output": f"Error: {error_message}",
                "execution_path": initial_state.get("execution_path", []),
                "execution_trace": initial_state.get("execution_trace", []),
                "node_outputs": initial_state.get("node_outputs", {}),
                "messages": [{"role": m.type, "content": m.content} for m in initial_state.get("messages", [])],
                "tool_results": initial_state.get("tool_results"),
                "input_metadata": initial_state.get("input_metadata"),
                "processed_input": initial_state.get("processed_input"),
                "llm_usage": initial_state.get("llm_usage"),
                "llm_cost": initial_state.get("llm_cost"),
                "audio_data": initial_state.get("audio_data"),
                "audio_format": initial_state.get("audio_format"),
                "twiml_response": initial_state.get("twiml_response"),
                "audio_transcript": initial_state.get("audio_transcript"),
                "error": error_message,
                # Session info even on error so caller can retry
                "session_id": session_id,
            }
