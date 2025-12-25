# Node-by-Node Execution Tracking & Visualization

## Overview
Enable users to see real-time execution flow through workflow nodes with detailed input/output data for each node, with a powerful templating system for data transformation between nodes.

**Goal**: When testing a workflow, users should be able to:
- See which nodes are being executed in real-time
- View the input data going into each node (as JSON)
- View the output data coming out of each node (as JSON)
- Use templating to extract and map specific keys from previous nodes
- Transform data between nodes using template expressions
- Track execution time and status for each node
- Replay execution flow step-by-step
- Debug issues by inspecting node-level data

## Key Concepts

### Data Flow Model
Each node in the workflow:
1. **Receives input** as JSON object
2. **Processes** the data according to its type
3. **Outputs** a JSON object
4. **Next nodes** can reference output keys using templates

### Templating System
Nodes can use **Jinja2-style templates** to reference data from previous nodes:
- `{{node_id.key}}` - Extract specific key from a node's output
- `{{input.field}}` - Reference from INPUT node
- `{{llm_agent.response}}` - Get LLM response
- `{{tool.result.data}}` - Access nested data from tool output

---

## 🔄 Data Flow & Templating Architecture

### Node Output Structure
Every node must output data in a **standardized JSON format**:

```json
{
  "node_id": "unique-node-id",
  "node_type": "INPUT|LLM_AGENT|TOOL|OUTPUT|etc",
  "data": {
    // Node-specific output data
    "key1": "value1",
    "key2": {"nested": "value"}
  },
  "metadata": {
    "timestamp": "2024-01-15T10:30:00Z",
    "duration_ms": 150
  }
}
```

### State Context
The execution state maintains a **context object** that accumulates all node outputs:

```python
state["node_outputs"] = {
    "input-1": {
        "message": "What is the weather?",
        "user_id": "user123",
        "timestamp": "2024-01-15T10:30:00Z"
    },
    "llm-1": {
        "response": "I'll check the weather for you",
        "tool_calls": [{"name": "get_weather", "args": {"city": "SF"}}],
        "tokens_used": 150
    },
    "tool-1": {
        "result": {
            "temperature": 72,
            "condition": "sunny",
            "city": "San Francisco"
        }
    }
}
```

### Template Resolution Examples

#### Example 1: Simple Field Reference
**Node Config:**
```json
{
  "id": "output-1",
  "type": "OUTPUT",
  "config": {
    "template": "The weather in {{tool-1.result.city}} is {{tool-1.result.condition}} and {{tool-1.result.temperature}}°F"
  }
}
```

**Resolved Output:**
```
"The weather in San Francisco is sunny and 72°F"
```

#### Example 2: Conditional Templates
**Node Config:**
```json
{
  "id": "llm-2",
  "type": "LLM_AGENT",
  "config": {
    "prompt_template": "User {{input-1.user_id}} asked: {{input-1.message}}\n{% if tool-1.result.temperature > 70 %}It's warm.{% else %}It's cool.{% endif %}"
  }
}
```

#### Example 3: Data Mapping
**Node Config:**
```json
{
  "id": "transform-1",
  "type": "TRANSFORM",
  "config": {
    "mapping": {
      "user": "{{input-1.user_id}}",
      "query": "{{input-1.message}}",
      "weather": {
        "temp": "{{tool-1.result.temperature}}",
        "status": "{{tool-1.result.condition}}"
      }
    }
  }
}
```

**Output:**
```json
{
  "user": "user123",
  "query": "What is the weather?",
  "weather": {
    "temp": 72,
    "status": "sunny"
  }
}
```

### Template Engine Implementation

**File**: `backend/app/services/template_engine.py` (new file)

```python
from jinja2 import Environment, BaseLoader, TemplateSyntaxError, UndefinedError
from typing import Dict, Any, Optional
import json
import re


class NodeTemplateEngine:
    """Template engine for resolving node references in workflow data."""

    def __init__(self):
        self.env = Environment(
            loader=BaseLoader(),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True
        )

        # Add custom filters
        self.env.filters['json'] = json.dumps
        self.env.filters['extract'] = self._extract_nested

    def _extract_nested(self, obj: Any, path: str) -> Any:
        """Extract nested value using dot notation."""
        keys = path.split('.')
        result = obj
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key)
            else:
                return None
        return result

    def resolve_template(
        self,
        template: str,
        context: Dict[str, Any],
        strict: bool = False
    ) -> str:
        """
        Resolve a template string using the context.

        Args:
            template: Template string with {{node_id.key}} references
            context: Dict of node_id -> output_data mappings
            strict: If True, raise error on undefined variables

        Returns:
            Resolved string
        """
        try:
            if strict:
                self.env.undefined = StrictUndefined

            tmpl = self.env.from_string(template)
            return tmpl.render(**context)

        except TemplateSyntaxError as e:
            raise ValueError(f"Template syntax error: {e}")
        except UndefinedError as e:
            if strict:
                raise ValueError(f"Undefined variable in template: {e}")
            return template

    def resolve_object(
        self,
        obj: Any,
        context: Dict[str, Any]
    ) -> Any:
        """
        Recursively resolve templates in an object (dict, list, or string).

        Args:
            obj: Object to resolve (can be dict, list, str, etc.)
            context: Context for template resolution

        Returns:
            Object with all templates resolved
        """
        if isinstance(obj, str):
            # Only resolve if it contains template markers
            if '{{' in obj and '}}' in obj:
                return self.resolve_template(obj, context)
            return obj

        elif isinstance(obj, dict):
            return {
                key: self.resolve_object(value, context)
                for key, value in obj.items()
            }

        elif isinstance(obj, list):
            return [
                self.resolve_object(item, context)
                for item in obj
            ]

        else:
            return obj

    def extract_dependencies(self, template: str) -> list[str]:
        """
        Extract node IDs that are referenced in a template.

        Args:
            template: Template string

        Returns:
            List of node IDs referenced
        """
        # Match {{node_id.something}}
        pattern = r'\{\{([a-zA-Z0-9_-]+)\.[^\}]+\}\}'
        matches = re.findall(pattern, template)
        return list(set(matches))


# Global instance
template_engine = NodeTemplateEngine()
```

### Integration with LangGraph Engine

**File**: `backend/app/services/langgraph_engine.py`

Add to `AgentState`:
```python
class AgentState(TypedDict):
    # ... existing fields ...
    node_outputs: Dict[str, Dict[str, Any]]  # Store all node outputs
    execution_trace: List[NodeExecutionTrace]
```

Update node handlers to:
1. **Store output in `node_outputs`**
2. **Resolve templates in node config**

Example for LLM Agent Node:
```python
def _handle_llm_agent_node(self, state: AgentState) -> AgentState:
    from app.services.template_engine import template_engine

    # Get node config
    nodes = state["agent_config"].get("nodes", [])
    current_node_id = state["current_node"]
    current_node = next((n for n in nodes if n.get("id") == current_node_id), None)
    node_config = current_node.get("data", {}).get("config", {})

    # Build context from previous node outputs
    context = state.get("node_outputs", {})

    # Resolve templates in system prompt
    system_prompt_template = node_config.get("system_prompt", "")
    system_prompt = template_engine.resolve_template(
        system_prompt_template,
        context
    )

    # Resolve templates in user message (if it's a template)
    user_message_template = node_config.get("user_message_template", "")
    if user_message_template:
        user_message = template_engine.resolve_template(
            user_message_template,
            context
        )
    else:
        # Use last message from state
        user_message = state["messages"][-1].content if state["messages"] else ""

    # ... call LLM with resolved prompts ...

    # Store output
    state["node_outputs"][current_node_id] = {
        "response": ai_response,
        "tool_calls": tool_calls,
        "tokens_used": tokens_used
    }

    return state
```

### Node Configuration Schema

Each node type can specify template fields in its config:

```typescript
// INPUT Node
{
  "id": "input-1",
  "type": "INPUT",
  "data": {
    "config": {
      "mode": "json",
      "schema": {...},
      // No templates needed - this is the source
    }
  }
}

// LLM_AGENT Node
{
  "id": "llm-1",
  "type": "LLM_AGENT",
  "data": {
    "config": {
      "model": "gpt-4",
      "system_prompt": "You are helping user {{input-1.user_id}}. Their question is: {{input-1.message}}",
      "temperature": 0.7,
      "tools": ["{{tool-1.name}}"]  // Can reference other nodes
    }
  }
}

// TOOL Node
{
  "id": "tool-1",
  "type": "TOOL",
  "data": {
    "config": {
      "tool_name": "get_weather",
      "arguments": {
        "city": "{{input-1.city}}",
        "units": "fahrenheit"
      }
    }
  }
}

// OUTPUT Node
{
  "id": "output-1",
  "type": "OUTPUT",
  "data": {
    "config": {
      "format": "text",
      "template": "Weather Report:\nCity: {{tool-1.result.city}}\nTemp: {{tool-1.result.temperature}}°F\nCondition: {{tool-1.result.condition}}\n\nAI Summary: {{llm-1.response}}"
    }
  }
}
```

### Frontend: Template Editor Component

**File**: `frontend/src/components/AgentBuilder/TemplateEditor.tsx` (new file)

```typescript
import React, { useState } from 'react';
import { Input, Tag, Tooltip, Space, Typography } from 'antd';
import { InfoCircleOutlined } from '@ant-design/icons';

const { TextArea } = Input;
const { Text } = Typography;

interface TemplateEditorProps {
  value: string;
  onChange: (value: string) => void;
  availableNodes: Array<{id: string; type: string; outputs: string[]}>;
  placeholder?: string;
}

export const TemplateEditor: React.FC<TemplateEditorProps> = ({
  value,
  onChange,
  availableNodes,
  placeholder
}) => {
  const [cursorPosition, setCursorPosition] = useState(0);

  const insertTemplate = (nodeId: string, key: string) => {
    const template = `{{${nodeId}.${key}}}`;
    const newValue =
      value.substring(0, cursorPosition) +
      template +
      value.substring(cursorPosition);
    onChange(newValue);
  };

  return (
    <div className="template-editor">
      <TextArea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onSelect={(e: any) => setCursorPosition(e.target.selectionStart)}
        placeholder={placeholder || "Use {{node_id.key}} to reference data"}
        rows={4}
        style={{ fontFamily: 'monospace' }}
      />

      <div className="mt-2">
        <Space size={[8, 8]} wrap>
          <Text type="secondary" strong style={{ fontSize: '12px' }}>
            Available References:
          </Text>
          {availableNodes.map(node => (
            <Tooltip
              key={node.id}
              title={
                <Space direction="vertical" size={0}>
                  {node.outputs.map(key => (
                    <Text key={key} style={{ color: 'white', fontSize: '11px' }}>
                      {`{{${node.id}.${key}}}`}
                    </Text>
                  ))}
                </Space>
              }
            >
              <Tag
                color="blue"
                style={{ cursor: 'pointer' }}
              >
                {node.id} ({node.type})
              </Tag>
            </Tooltip>
          ))}
        </Space>
      </div>

      <div className="mt-2">
        <Text type="secondary" style={{ fontSize: '11px' }}>
          <InfoCircleOutlined /> Click on a tag to see available keys.
          Use dot notation for nested values: {{`{{node.result.data.field}}`}}
        </Text>
      </div>
    </div>
  );
};
```

### Data Flow Visualization

In the execution trace, show data transformations:

```json
{
  "node_id": "llm-1",
  "node_type": "LLM_AGENT",
  "input_data": {
    "system_prompt_template": "Help user {{input-1.user_id}}",
    "system_prompt_resolved": "Help user user123",
    "context_used": {
      "input-1.user_id": "user123",
      "input-1.message": "What is the weather?"
    }
  },
  "output_data": {
    "response": "I'll check that for you",
    "tokens_used": 150
  }
}
```

---

## 📋 Backend Changes

### 1. Enhanced Execution Tracking Data Structure

**File**: `backend/app/services/langgraph_engine.py`

Add new data structure for detailed node execution:

```python
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
    metadata: Optional[Dict[str, Any]]  # Additional info like tokens, model used, etc.
```

Update `AgentState` to include:
```python
class AgentState(TypedDict):
    # ... existing fields ...
    execution_trace: List[NodeExecutionTrace]  # Add this field
```

### 2. Modify All Node Handlers

Update each node handler to capture input/output snapshots.

**Pattern to follow:**
```python
def _handle_input_node(self, state: AgentState) -> AgentState:
    start_time = datetime.now()

    # Get node info
    nodes = state["agent_config"].get("nodes", [])
    current_node_id = state["current_node"]
    current_node = next((n for n in nodes if n.get("id") == current_node_id), None)
    node_label = current_node.get("data", {}).get("label", "Input Node") if current_node else "Input Node"

    # Capture input state
    input_snapshot = {
        "raw_input": state.get("raw_input"),
        "messages": [msg.content for msg in state.get("messages", [])]
    }

    try:
        # ... existing node logic ...
        # Example: process input, validate, etc.

        # Capture output state
        output_snapshot = {
            "processed_input": state.get("processed_input"),
            "validation_passed": state.get("input_metadata", {}).get("validation_passed", True),
            "validation_errors": state.get("input_metadata", {}).get("errors", [])
        }

        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds() * 1000

        # Log trace
        state["execution_trace"].append({
            "node_id": current_node_id,
            "node_type": "INPUT",
            "node_label": node_label,
            "input_data": input_snapshot,
            "output_data": output_snapshot,
            "timestamp": datetime.now().isoformat(),
            "duration_ms": int(duration),
            "status": "success",
            "error": None,
            "metadata": state.get("input_metadata")
        })

    except Exception as e:
        # Log error trace
        duration = (datetime.now() - start_time).total_seconds() * 1000
        state["execution_trace"].append({
            "node_id": current_node_id,
            "node_type": "INPUT",
            "node_label": node_label,
            "input_data": input_snapshot,
            "output_data": None,
            "timestamp": datetime.now().isoformat(),
            "duration_ms": int(duration),
            "status": "error",
            "error": str(e),
            "metadata": None
        })
        raise

    state["execution_path"].append("INPUT")
    return state
```

**Apply this pattern to all node handlers:**
- `_handle_input_node`
  - Input: raw_input, mode
  - Output: processed_input, validation result

- `_handle_llm_agent_node`
  - Input: messages, system prompt, tools available
  - Output: AI response, tool calls, tokens used

- `_handle_output_node`
  - Input: messages, llm response
  - Output: formatted final output

- `_handle_decision_node`
  - Input: condition, current state
  - Output: decision result, next node

- `_handle_tool_node`
  - Input: tool name, tool arguments
  - Output: tool result

- `_handle_memory_node`
  - Input: session_id, query
  - Output: retrieved conversation history

- `_handle_rag_node`
  - Input: query, collection name
  - Output: retrieved documents

### 3. Initialize execution_trace in execute_agent

**File**: `backend/app/services/langgraph_engine.py`

```python
async def execute_agent(self, agent_config: dict, user_input: Any, input_mode: Optional[str] = None) -> dict:
    graph = self.build_graph_from_config(agent_config)

    initial_state = {
        "messages": [],
        "agent_config": agent_config,
        "current_node": "",
        "execution_path": [],
        "execution_trace": [],  # Initialize this
        "tool_results": {},
        # ... rest of initialization ...
    }

    result = await graph.ainvoke(initial_state)

    return {
        "output": result.get("final_output"),
        "execution_path": result.get("execution_path"),
        "execution_trace": result.get("execution_trace", []),  # Return this
        # ... rest of response ...
    }
```

### 4. Update Execute Endpoint Response

**File**: `backend/app/api/v1/execute.py`

Update `ExecuteResponse` model:
```python
class ExecuteResponse(BaseModel):
    """Response model for agent execution."""
    execution_id: UUID
    output: Optional[str]
    execution_path: list
    execution_trace: List[Dict[str, Any]]  # Add this
    tokens_used: int
    execution_time: int
    input_metadata: Optional[Dict[str, Any]] = None
    processed_input: Optional[Dict[str, Any]] = None
```

Update the endpoint return:
```python
@router.post("/{agent_id}")
async def execute_agent(
    agent_id: UUID,
    request: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    # ... existing code ...

    execution_result = await engine.execute_agent(
        agent_config=agent.config,
        user_input=agent_input,
        input_mode=request.mode
    )

    return ExecuteResponse(
        execution_id=execution.id,
        output=execution_result.get("output"),
        execution_path=execution_result.get("execution_path", []),
        execution_trace=execution_result.get("execution_trace", []),  # Add this
        tokens_used=tokens_used,
        execution_time=execution_time,
        input_metadata=execution_result.get("input_metadata"),
        processed_input=execution_result.get("processed_input"),
    )
```

### 5. Enhanced Streaming Endpoint (Optional - Phase 3)

**File**: `backend/app/api/v1/execute.py`

For real-time visualization, enhance streaming to emit node traces:

```python
@router.post("/{agent_id}/stream")
async def execute_agent_stream(
    agent_id: UUID,
    request: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """Execute an agent with streaming response."""

    async def generate():
        yield f"data: {json.dumps({'type': 'start'})}\n\n"

        engine = LangGraphEngine(db=db, redis_client=redis)

        # Execute and stream node traces
        execution_result = await engine.execute_agent(
            agent_config=agent.config,
            user_input=agent_input,
            input_mode=request.mode
        )

        # Stream each node execution
        for trace in execution_result.get("execution_trace", []):
            yield f"data: {json.dumps({'type': 'node_trace', 'data': trace})}\n\n"
            await asyncio.sleep(0.2)  # Delay for visualization

        # Stream final output
        yield f"data: {json.dumps({
            'type': 'complete',
            'output': execution_result.get('output'),
            'tokens_used': execution_result.get('llm_usage', {}).get('total_tokens', 0)
        })}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

---

## 🎨 Frontend Changes

### 6. Create Type Definitions

**File**: `frontend/src/types/execution.ts` (new file)

```typescript
export interface NodeExecutionTrace {
  node_id: string;
  node_type: string;
  node_label: string;
  input_data: Record<string, any> | null;
  output_data: Record<string, any> | null;
  timestamp: string;
  duration_ms: number | null;
  status: 'success' | 'error' | 'skipped' | 'running';
  error: string | null;
  metadata?: Record<string, any>;
}

export interface ExecutionResult {
  execution_id: string;
  output: string | null;
  execution_path: string[];
  execution_trace: NodeExecutionTrace[];
  tokens_used: number;
  execution_time: number;
  input_metadata?: Record<string, any>;
  processed_input?: Record<string, any>;
}
```

### 7. Create JSON Viewer Component

**File**: `frontend/src/components/Common/JSONViewer.tsx` (new file)

```typescript
import React, { useState } from 'react';
import { Typography, Button } from 'antd';
import { CopyOutlined, CheckOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface JSONViewerProps {
  data: any;
  maxHeight?: number;
}

export const JSONViewer: React.FC<JSONViewerProps> = ({ data, maxHeight = 300 }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="json-viewer-container">
      <div className="flex justify-end mb-2">
        <Button
          size="small"
          icon={copied ? <CheckOutlined /> : <CopyOutlined />}
          onClick={handleCopy}
        >
          {copied ? 'Copied' : 'Copy'}
        </Button>
      </div>
      <pre
        className="json-viewer"
        style={{
          background: '#f5f5f5',
          padding: '12px',
          borderRadius: '4px',
          maxHeight: `${maxHeight}px`,
          overflow: 'auto',
          fontSize: '12px',
          fontFamily: 'monospace',
        }}
      >
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
};
```

### 8. Create NodeExecutionViewer Component

**File**: `frontend/src/components/Testing/NodeExecutionViewer.tsx` (new file)

```typescript
import React from 'react';
import { Card, Tag, Space, Typography, Collapse, Alert } from 'antd';
import { ClockCircleOutlined, CheckCircleOutlined, CloseCircleOutlined, MinusCircleOutlined } from '@ant-design/icons';
import { JSONViewer } from '../Common/JSONViewer';
import type { NodeExecutionTrace } from '../../types/execution';

const { Text } = Typography;
const { Panel } = Collapse;

interface NodeExecutionViewerProps {
  trace: NodeExecutionTrace;
  isActive?: boolean;
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'success':
      return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
    case 'error':
      return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
    case 'running':
      return <ClockCircleOutlined style={{ color: '#1890ff' }} spin />;
    case 'skipped':
      return <MinusCircleOutlined style={{ color: '#d9d9d9' }} />;
    default:
      return null;
  }
};

const getStatusColor = (status: string): string => {
  switch (status) {
    case 'success': return 'success';
    case 'error': return 'error';
    case 'running': return 'processing';
    case 'skipped': return 'default';
    default: return 'default';
  }
};

export const NodeExecutionViewer: React.FC<NodeExecutionViewerProps> = ({ trace, isActive = false }) => {
  return (
    <Card
      size="small"
      className={`node-execution-card ${isActive ? 'active-node' : ''}`}
      style={{
        border: isActive ? '2px solid #1890ff' : '1px solid #d9d9d9',
        boxShadow: isActive ? '0 2px 8px rgba(24, 144, 255, 0.2)' : 'none',
      }}
      title={
        <div className="flex items-center justify-between">
          <Space>
            {getStatusIcon(trace.status)}
            <Text strong>{trace.node_label}</Text>
            <Tag color="blue">{trace.node_type}</Tag>
            <Tag color={getStatusColor(trace.status)}>{trace.status}</Tag>
          </Space>
          {trace.duration_ms && (
            <Text type="secondary" style={{ fontSize: '12px' }}>
              <ClockCircleOutlined /> {trace.duration_ms}ms
            </Text>
          )}
        </div>
      }
    >
      <div className="mb-2">
        <Text type="secondary" style={{ fontSize: '11px' }}>
          {new Date(trace.timestamp).toLocaleString()}
        </Text>
      </div>

      {trace.error && (
        <Alert
          type="error"
          message="Execution Error"
          description={trace.error}
          showIcon
          style={{ marginBottom: 12 }}
        />
      )}

      <Collapse defaultActiveKey={isActive ? ['input', 'output'] : []}>
        <Panel header="Input Data" key="input">
          {trace.input_data ? (
            <JSONViewer data={trace.input_data} maxHeight={200} />
          ) : (
            <Text type="secondary">No input data</Text>
          )}
        </Panel>

        <Panel header="Output Data" key="output">
          {trace.output_data ? (
            <JSONViewer data={trace.output_data} maxHeight={200} />
          ) : (
            <Text type="secondary">No output data</Text>
          )}
        </Panel>

        {trace.metadata && Object.keys(trace.metadata).length > 0 && (
          <Panel header="Metadata" key="metadata">
            <JSONViewer data={trace.metadata} maxHeight={150} />
          </Panel>
        )}
      </Collapse>
    </Card>
  );
};
```

### 9. Create ExecutionFlowVisualizer Component

**File**: `frontend/src/components/Testing/ExecutionFlowVisualizer.tsx` (new file)

```typescript
import React, { useState } from 'react';
import { Timeline, Card, Space, Button, Slider, Typography } from 'antd';
import { PlayCircleOutlined, PauseCircleOutlined, StepBackwardOutlined, StepForwardOutlined } from '@ant-design/icons';
import { NodeExecutionViewer } from './NodeExecutionViewer';
import type { NodeExecutionTrace } from '../../types/execution';

const { Title, Text } = Typography;

interface ExecutionFlowVisualizerProps {
  traces: NodeExecutionTrace[];
  showPlayback?: boolean;
}

const getTimelineColor = (status: string): string => {
  switch (status) {
    case 'success': return 'green';
    case 'error': return 'red';
    case 'running': return 'blue';
    case 'skipped': return 'gray';
    default: return 'gray';
  }
};

export const ExecutionFlowVisualizer: React.FC<ExecutionFlowVisualizerProps> = ({
  traces,
  showPlayback = true
}) => {
  const [currentStep, setCurrentStep] = useState(traces.length - 1);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1000); // ms per step

  React.useEffect(() => {
    if (isPlaying && currentStep < traces.length - 1) {
      const timer = setTimeout(() => {
        setCurrentStep(prev => prev + 1);
      }, playbackSpeed);
      return () => clearTimeout(timer);
    } else if (isPlaying && currentStep === traces.length - 1) {
      setIsPlaying(false);
    }
  }, [isPlaying, currentStep, traces.length, playbackSpeed]);

  const handlePlay = () => {
    if (currentStep === traces.length - 1) {
      setCurrentStep(0);
    }
    setIsPlaying(!isPlaying);
  };

  const handlePrevious = () => {
    setIsPlaying(false);
    setCurrentStep(prev => Math.max(0, prev - 1));
  };

  const handleNext = () => {
    setIsPlaying(false);
    setCurrentStep(prev => Math.min(traces.length - 1, prev + 1));
  };

  const handleReset = () => {
    setIsPlaying(false);
    setCurrentStep(0);
  };

  if (traces.length === 0) {
    return (
      <Card>
        <Text type="secondary">No execution data available</Text>
      </Card>
    );
  }

  return (
    <div className="execution-flow-visualizer">
      <Card
        title={
          <div className="flex items-center justify-between">
            <Title level={5} style={{ margin: 0 }}>
              Execution Flow
            </Title>
            <Text type="secondary">
              {traces.length} node{traces.length !== 1 ? 's' : ''} executed
            </Text>
          </div>
        }
      >
        {showPlayback && (
          <div className="playback-controls mb-4 p-3 bg-gray-50 rounded">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div className="flex items-center justify-between">
                <Space>
                  <Button
                    icon={<StepBackwardOutlined />}
                    onClick={handlePrevious}
                    disabled={currentStep === 0}
                    size="small"
                  />
                  <Button
                    type="primary"
                    icon={isPlaying ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                    onClick={handlePlay}
                    size="small"
                  >
                    {isPlaying ? 'Pause' : 'Play'}
                  </Button>
                  <Button
                    icon={<StepForwardOutlined />}
                    onClick={handleNext}
                    disabled={currentStep === traces.length - 1}
                    size="small"
                  />
                  <Button onClick={handleReset} size="small">
                    Reset
                  </Button>
                </Space>
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  Step {currentStep + 1} of {traces.length}
                </Text>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: '11px' }}>Playback Progress:</Text>
                <Slider
                  min={0}
                  max={traces.length - 1}
                  value={currentStep}
                  onChange={(value) => {
                    setIsPlaying(false);
                    setCurrentStep(value);
                  }}
                  tooltip={{ formatter: (value) => `Step ${(value || 0) + 1}` }}
                />
              </div>
            </Space>
          </div>
        )}

        <Timeline mode="left">
          {traces.map((trace, index) => (
            <Timeline.Item
              key={`${trace.node_id}-${index}`}
              color={getTimelineColor(trace.status)}
              style={{
                opacity: showPlayback && index > currentStep ? 0.3 : 1,
                transition: 'opacity 0.3s ease',
              }}
            >
              <NodeExecutionViewer
                trace={trace}
                isActive={showPlayback && index === currentStep}
              />
            </Timeline.Item>
          ))}
        </Timeline>
      </Card>
    </div>
  );
};
```

### 10. Update AgentPlayground Component

**File**: `frontend/src/components/Testing/AgentPlayground.tsx`

Add execution trace visualization:

```typescript
import { ExecutionFlowVisualizer } from './ExecutionFlowVisualizer';
import type { NodeExecutionTrace } from '../../types/execution';

// Add state
const [executionTrace, setExecutionTrace] = useState<NodeExecutionTrace[]>([]);
const [showExecutionFlow, setShowExecutionFlow] = useState(true);

// Update handleSend to capture execution trace
const data = await response.json();

// Store execution trace
if (data.execution_trace) {
  setExecutionTrace(data.execution_trace);
}

// Update UI layout
return (
  <div className="h-full flex flex-col">
    <div className="mb-3 flex justify-between items-center">
      <Title level={4}>{agentName} - Test Playground</Title>
      <Space>
        <Button
          type={showExecutionFlow ? 'primary' : 'default'}
          onClick={() => setShowExecutionFlow(!showExecutionFlow)}
          size="small"
        >
          {showExecutionFlow ? 'Hide' : 'Show'} Execution Flow
        </Button>
      </Space>
    </div>

    <div className="flex-1 flex gap-4">
      {/* Chat Interface */}
      <div className={showExecutionFlow ? 'w-1/2' : 'w-full'}>
        <Card>
          {/* Existing chat interface code */}
        </Card>
      </div>

      {/* Execution Flow Visualization */}
      {showExecutionFlow && (
        <div className="w-1/2 overflow-y-auto">
          <ExecutionFlowVisualizer
            traces={executionTrace}
            showPlayback={true}
          />
        </div>
      )}
    </div>
  </div>
);
```

### 11. Add Visual Highlighting to Workflow Canvas (Optional - Phase 2)

**File**: `frontend/src/components/AgentBuilder/AgentCanvas.tsx`

Add execution overlay:

```typescript
interface AgentCanvasProps {
  // ... existing props
  executionTrace?: NodeExecutionTrace[];
  highlightExecutingNode?: boolean;
}

// In render, add execution status to nodes
const nodeTypes = useMemo(
  () => ({
    inputNode: (props: NodeProps) => (
      <InputNode
        {...props}
        executionStatus={getNodeExecutionStatus(props.id, executionTrace)}
      />
    ),
    // ... other node types with execution status
  }),
  [executionTrace]
);

// Helper function
const getNodeExecutionStatus = (nodeId: string, traces?: NodeExecutionTrace[]) => {
  if (!traces) return null;
  return traces.find(trace => trace.node_id === nodeId);
};
```

### 12. Update BaseNode to Show Execution Status

**File**: `frontend/src/components/AgentBuilder/nodes/BaseNode.tsx`

```typescript
interface BaseNodeProps {
  data: any;
  executionStatus?: NodeExecutionTrace | null;
}

export const BaseNode: React.FC<BaseNodeProps> = ({ data, executionStatus }) => {
  const getStatusBorder = () => {
    if (!executionStatus) return '2px solid #d9d9d9';
    switch (executionStatus.status) {
      case 'success': return '3px solid #52c41a';
      case 'error': return '3px solid #ff4d4f';
      case 'running': return '3px solid #1890ff';
      default: return '2px solid #d9d9d9';
    }
  };

  return (
    <div
      className="base-node"
      style={{
        border: getStatusBorder(),
        boxShadow: executionStatus ? '0 4px 12px rgba(0,0,0,0.15)' : 'none',
      }}
    >
      {executionStatus && (
        <div className="execution-badge">
          <Tag color={executionStatus.status === 'success' ? 'success' : 'error'}>
            {executionStatus.duration_ms}ms
          </Tag>
        </div>
      )}
      {/* Rest of node content */}
    </div>
  );
};
```

---

## 🎯 Implementation Phases

### Phase 1: Core Tracking (Week 1)
**Priority: HIGH - Essential for basic functionality**

1. Backend Changes:
   - [ ] Add `NodeExecutionTrace` TypedDict
   - [ ] Add `execution_trace` to `AgentState`
   - [ ] Update `_handle_input_node` with tracing
   - [ ] Update `_handle_llm_agent_node` with tracing
   - [ ] Update `_handle_output_node` with tracing
   - [ ] Update `ExecuteResponse` model
   - [ ] Return `execution_trace` in execute endpoint

2. Frontend Changes:
   - [ ] Create `execution.ts` type definitions
   - [ ] Create `JSONViewer` component
   - [ ] Create basic `NodeExecutionViewer` component
   - [ ] Update `AgentPlayground` to display trace

**Deliverable**: Users can see input/output for each node after execution completes

### Phase 2: Enhanced Visualization (Week 2)
**Priority: MEDIUM - Improves user experience**

3. Backend Changes:
   - [ ] Update remaining node handlers (TOOL, MEMORY, RAG, DECISION)
   - [ ] Add more detailed metadata to traces

4. Frontend Changes:
   - [ ] Create `ExecutionFlowVisualizer` with Timeline
   - [ ] Add playback controls (play, pause, step)
   - [ ] Add execution highlighting to workflow canvas
   - [ ] Update `BaseNode` to show execution status

**Deliverable**: Users can replay execution step-by-step and see visual feedback

### Phase 3: Real-time Streaming (Week 3)
**Priority: LOW - Nice to have**

5. Backend Changes:
   - [ ] Implement streaming execution endpoint
   - [ ] Emit traces as nodes execute

6. Frontend Changes:
   - [ ] Connect to streaming endpoint
   - [ ] Show real-time execution progress
   - [ ] Add live node highlighting during execution

**Deliverable**: Users see nodes execute in real-time

---

## 📊 Example Data Flow

### Input
```json
{
  "input": "What is the weather in San Francisco?",
  "mode": "chat",
  "session_id": "session_123"
}
```

### Execution Trace Output
```json
{
  "execution_id": "exec-456",
  "output": "The weather in San Francisco is sunny and 72°F",
  "execution_path": ["INPUT", "LLM_AGENT", "TOOL", "OUTPUT"],
  "execution_trace": [
    {
      "node_id": "input-1",
      "node_type": "INPUT",
      "node_label": "User Input",
      "input_data": {
        "raw_input": "What is the weather in San Francisco?",
        "mode": "chat"
      },
      "output_data": {
        "processed_input": {
          "message": "What is the weather in San Francisco?"
        },
        "validation_passed": true
      },
      "timestamp": "2024-01-15T10:30:00.000Z",
      "duration_ms": 5,
      "status": "success",
      "error": null
    },
    {
      "node_id": "llm-1",
      "node_type": "LLM_AGENT",
      "node_label": "Main Agent",
      "input_data": {
        "messages": ["What is the weather in San Francisco?"],
        "tools": ["get_weather"],
        "system_prompt": "You are a helpful assistant..."
      },
      "output_data": {
        "response": "I'll check the weather for you.",
        "tool_calls": [
          {
            "name": "get_weather",
            "args": {
              "location": "San Francisco"
            }
          }
        ]
      },
      "timestamp": "2024-01-15T10:30:00.100Z",
      "duration_ms": 1200,
      "status": "success",
      "error": null,
      "metadata": {
        "model": "gpt-4",
        "tokens": {
          "prompt": 50,
          "completion": 100,
          "total": 150
        }
      }
    },
    {
      "node_id": "tool-1",
      "node_type": "TOOL",
      "node_label": "Weather Tool",
      "input_data": {
        "tool_name": "get_weather",
        "arguments": {
          "location": "San Francisco"
        }
      },
      "output_data": {
        "result": "Sunny, 72°F"
      },
      "timestamp": "2024-01-15T10:30:01.300Z",
      "duration_ms": 450,
      "status": "success",
      "error": null
    },
    {
      "node_id": "output-1",
      "node_type": "OUTPUT",
      "node_label": "Final Output",
      "input_data": {
        "llm_response": "The weather in San Francisco is sunny and 72°F",
        "format": "text"
      },
      "output_data": {
        "final_output": "The weather in San Francisco is sunny and 72°F"
      },
      "timestamp": "2024-01-15T10:30:01.750Z",
      "duration_ms": 2,
      "status": "success",
      "error": null
    }
  ],
  "tokens_used": 150,
  "execution_time": 1750
}
```

---

## 🧪 Testing Strategy

### Unit Tests
1. Test each node handler captures correct input/output
2. Test error scenarios log error traces
3. Test trace serialization/deserialization

### Integration Tests
1. Test full workflow execution with trace
2. Test streaming endpoint emits traces
3. Test trace persistence in database

### E2E Tests
1. Test UI displays execution trace correctly
2. Test playback controls work
3. Test node highlighting on canvas

---

## 🚀 Success Metrics

1. **Functionality**: All nodes capture input/output correctly
2. **Performance**: Tracing adds <10% overhead to execution time
3. **UX**: Users can easily debug failed executions
4. **Adoption**: 80% of users use execution view when testing

---

## 📝 Notes & Considerations

### Performance
- Execution trace can get large for complex workflows
- Consider limiting trace data size (e.g., truncate large objects)
- Add pagination for very long execution traces

### Storage
- Store execution traces in database for history
- Consider retention policy (e.g., keep last 100 executions)
- Option to export traces as JSON

### Privacy
- Be careful with sensitive data in traces
- Add option to redact/mask certain fields
- Respect data privacy regulations

### Future Enhancements
- Compare multiple execution traces side-by-side
- Export execution trace as report
- Integration with monitoring/observability tools
- Add breakpoints for step-through debugging
- Show branch/conditional logic in visualization

---

## 🔗 Related Documents
- [Agent Configuration Schema](./agent-config-schema.md)
- [Node Types Documentation](./node-types.md)
- [API Documentation](../backend/docs/api.md)
