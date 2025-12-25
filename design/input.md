# INPUT Node Enhancement Proposal

## Executive Summary

This document proposes enhancements to the INPUT node to support multiple input modes (Chat, JSON, Form), inspired by n8n's chat trigger and industry best practices. The current INPUT node is a simple pass-through; the enhanced version will provide flexible input handling for diverse agent use cases.

---

## Current State Analysis

### Frontend (`InputNode.tsx`)
```typescript
// Current implementation - simple visual component
export const InputNode = (props: NodeProps) => {
  return (
    <BaseNode
      {...props}
      icon={<LoginOutlined />}
      color="#52c41a"
      hasInput={false}  // No configuration
    />
  );
};
```

**Limitations:**
- No configuration options
- No input type specification
- No validation schema
- No default values
- No input transformation capabilities

### Backend (`langgraph_engine.py`)
```python
def _handle_input_node(self, state: AgentState) -> AgentState:
    """Handle INPUT node - initialize agent state."""
    state["execution_path"].append("INPUT")
    return state  # Simple pass-through
```

**Limitations:**
- No input validation
- No schema enforcement
- No type conversion
- Assumes all input is chat-style string
- No support for structured data

---

## Proposed Enhancements

### 1. Input Modes

Support three distinct input modes:

#### **A. Chat Mode** (Default)
- **Use Case**: Conversational agents, chatbots, Q&A systems
- **Input Format**: Plain text string
- **Features**:
  - Optional chat history support
  - Session management
  - Message metadata (timestamp, user_id, etc.)
  - System message configuration

#### **B. JSON Mode**
- **Use Case**: API integrations, webhooks, structured workflows
- **Input Format**: JSON object with schema validation
- **Features**:
  - JSON schema definition
  - Validation with error messages
  - Type coercion (string → number, etc.)
  - Required/optional field specification
  - Default values

#### **C. Form Mode**
- **Use Case**: User-facing forms, data collection, surveys
- **Input Format**: Key-value pairs with field definitions
- **Features**:
  - Field type specification (text, number, select, multiselect, date)
  - Validation rules (min/max, regex, required)
  - Field dependencies (conditional fields)
  - Help text and placeholders
  - Default values

---

## Configuration Schema

### Node Data Structure
```typescript
interface InputNodeConfig {
  // Basic properties
  label: string;
  description?: string;

  // Input mode configuration
  mode: 'chat' | 'json' | 'form';

  // Chat mode specific
  chatConfig?: {
    systemMessage?: string;
    includeHistory?: boolean;
    maxHistoryMessages?: number;
    enableStreaming?: boolean;
    metadata?: {
      collectUserId?: boolean;
      collectTimestamp?: boolean;
      customFields?: Array<{
        key: string;
        label: string;
        type: 'string' | 'number' | 'boolean';
      }>;
    };
  };

  // JSON mode specific
  jsonConfig?: {
    schema: {
      type: 'object';
      properties: Record<string, {
        type: 'string' | 'number' | 'boolean' | 'array' | 'object';
        description?: string;
        required?: boolean;
        default?: any;
        enum?: any[];
        minimum?: number;
        maximum?: number;
        pattern?: string;
      }>;
      required?: string[];
    };
    validateOnInput?: boolean;
    coerceTypes?: boolean;
    additionalProperties?: boolean;
  };

  // Form mode specific
  formConfig?: {
    fields: Array<{
      key: string;
      label: string;
      type: 'text' | 'textarea' | 'number' | 'select' | 'multiselect' | 'date' | 'checkbox' | 'radio';
      required?: boolean;
      default?: any;
      placeholder?: string;
      helpText?: string;

      // Validation
      validation?: {
        min?: number;
        max?: number;
        minLength?: number;
        maxLength?: number;
        pattern?: string;
        customMessage?: string;
      };

      // For select/radio
      options?: Array<{
        label: string;
        value: string | number;
      }>;

      // Conditional rendering
      dependsOn?: {
        field: string;
        value: any;
      };
    }>;
  };

  // Output transformation
  outputMapping?: {
    extractFields?: string[];
    renameFields?: Record<string, string>;
    transformations?: Array<{
      field: string;
      operation: 'uppercase' | 'lowercase' | 'trim' | 'parse_json' | 'format_date';
    }>;
  };
}
```

---

## Backend Implementation

### Updated State Handling

```python
from typing import Any, Dict, Optional
from pydantic import BaseModel, ValidationError
import jsonschema
from datetime import datetime

class InputNodeHandler:
    """Enhanced INPUT node handler with mode support."""

    def _handle_input_node(self, state: AgentState) -> AgentState:
        """Handle INPUT node with multiple mode support."""
        state["execution_path"].append("INPUT")

        # Get node configuration
        node_config = self._get_node_config(state, "INPUT")
        mode = node_config.get("mode", "chat")

        # Get raw input from execution request
        raw_input = state.get("raw_input")

        # Process based on mode
        if mode == "chat":
            processed_input = self._process_chat_input(raw_input, node_config)
        elif mode == "json":
            processed_input = self._process_json_input(raw_input, node_config)
        elif mode == "form":
            processed_input = self._process_form_input(raw_input, node_config)
        else:
            raise ValueError(f"Unsupported input mode: {mode}")

        # Store processed input in state
        state["processed_input"] = processed_input
        state["input_metadata"] = {
            "mode": mode,
            "timestamp": datetime.utcnow().isoformat(),
            "validation_passed": True,
        }

        # Convert to message format for LangGraph
        if mode == "chat":
            message_content = processed_input.get("message", raw_input)
        else:
            message_content = json.dumps(processed_input)

        state["messages"].append(HumanMessage(content=message_content))

        return state

    def _process_chat_input(self, raw_input: Any, config: Dict) -> Dict:
        """Process chat mode input."""
        chat_config = config.get("chatConfig", {})

        result = {
            "message": str(raw_input),
            "mode": "chat",
        }

        # Add system message if configured
        if system_msg := chat_config.get("systemMessage"):
            result["system_message"] = system_msg

        # Add metadata if configured
        if metadata_config := chat_config.get("metadata", {}):
            result["metadata"] = {}
            if metadata_config.get("collectTimestamp"):
                result["metadata"]["timestamp"] = datetime.utcnow().isoformat()
            # Add other metadata fields...

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
                raise ValueError(f"Invalid JSON input: {e}")
        else:
            data = raw_input

        # Validate against schema if provided
        if schema and json_config.get("validateOnInput", True):
            try:
                jsonschema.validate(instance=data, schema=schema)
            except jsonschema.ValidationError as e:
                raise ValueError(f"JSON validation failed: {e.message}")

        # Type coercion if enabled
        if json_config.get("coerceTypes"):
            data = self._coerce_types(data, schema)

        # Apply defaults
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
                raise ValueError("Form input must be valid JSON")
        else:
            data = raw_input

        result = {}
        errors = []

        # Validate each field
        for field in fields:
            key = field["key"]
            value = data.get(key)

            # Check required
            if field.get("required") and value is None:
                errors.append(f"Field '{key}' is required")
                continue

            # Apply default
            if value is None and "default" in field:
                value = field["default"]

            # Type validation and conversion
            if value is not None:
                field_type = field["type"]

                if field_type == "number":
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        errors.append(f"Field '{key}' must be a number")
                        continue

                # Validation rules
                if validation := field.get("validation"):
                    if "min" in validation and value < validation["min"]:
                        errors.append(f"Field '{key}' must be >= {validation['min']}")
                    if "max" in validation and value > validation["max"]:
                        errors.append(f"Field '{key}' must be <= {validation['max']}")
                    # Add more validation...

            result[key] = value

        if errors:
            raise ValueError(f"Form validation failed: {'; '.join(errors)}")

        return result
```

---

## Frontend Implementation

### Property Panel Update

```typescript
// Add to PropertyPanel.tsx
{selectedNode.data.type === 'INPUT' && (
  <>
    <Form.Item name={['config', 'mode']} label="Input Mode" initialValue="chat">
      <Select
        options={[
          { label: 'Chat', value: 'chat' },
          { label: 'JSON', value: 'json' },
          { label: 'Form', value: 'form' },
        ]}
      />
    </Form.Item>

    <Form.Item noStyle shouldUpdate>
      {() => {
        const mode = form.getFieldValue(['config', 'mode']);

        if (mode === 'chat') {
          return (
            <Card size="small" title="Chat Configuration" className="mb-3">
              <Form.Item
                name={['config', 'chatConfig', 'systemMessage']}
                label="System Message"
                tooltip="Optional system message to set context"
              >
                <TextArea rows={3} placeholder="You are a helpful assistant..." />
              </Form.Item>

              <Form.Item
                name={['config', 'chatConfig', 'includeHistory']}
                valuePropName="checked"
              >
                <Checkbox>Include chat history</Checkbox>
              </Form.Item>

              {form.getFieldValue(['config', 'chatConfig', 'includeHistory']) && (
                <Form.Item
                  name={['config', 'chatConfig', 'maxHistoryMessages']}
                  label="Max History Messages"
                >
                  <InputNumber min={1} max={50} />
                </Form.Item>
              )}
            </Card>
          );
        }

        if (mode === 'json') {
          return (
            <Card size="small" title="JSON Configuration" className="mb-3">
              <Form.Item
                name={['config', 'jsonConfig', 'schema']}
                label="JSON Schema"
                tooltip="Define the expected JSON structure"
              >
                <TextArea
                  rows={10}
                  placeholder={`{
  "type": "object",
  "properties": {
    "name": { "type": "string" },
    "age": { "type": "number" }
  },
  "required": ["name"]
}`}
                />
              </Form.Item>

              <Form.Item
                name={['config', 'jsonConfig', 'validateOnInput']}
                valuePropName="checked"
                initialValue={true}
              >
                <Checkbox>Validate on input</Checkbox>
              </Form.Item>

              <Form.Item
                name={['config', 'jsonConfig', 'coerceTypes']}
                valuePropName="checked"
              >
                <Checkbox>Coerce types automatically</Checkbox>
              </Form.Item>
            </Card>
          );
        }

        if (mode === 'form') {
          return (
            <Card size="small" title="Form Configuration" className="mb-3">
              <FormFieldBuilder
                value={form.getFieldValue(['config', 'formConfig', 'fields'])}
                onChange={(fields) =>
                  form.setFieldValue(['config', 'formConfig', 'fields'], fields)
                }
              />
            </Card>
          );
        }

        return null;
      }}
    </Form.Item>
  </>
)}
```

### FormFieldBuilder Component (new)

```typescript
// components/AgentBuilder/FormFieldBuilder.tsx
interface FormFieldBuilderProps {
  value?: FormField[];
  onChange?: (fields: FormField[]) => void;
}

export const FormFieldBuilder = ({ value = [], onChange }: FormFieldBuilderProps) => {
  const [fields, setFields] = useState<FormField[]>(value);

  const addField = () => {
    const newFields = [...fields, {
      key: `field_${Date.now()}`,
      label: 'New Field',
      type: 'text',
      required: false,
    }];
    setFields(newFields);
    onChange?.(newFields);
  };

  const removeField = (index: number) => {
    const newFields = fields.filter((_, i) => i !== index);
    setFields(newFields);
    onChange?.(newFields);
  };

  const updateField = (index: number, updates: Partial<FormField>) => {
    const newFields = [...fields];
    newFields[index] = { ...newFields[index], ...updates };
    setFields(newFields);
    onChange?.(newFields);
  };

  return (
    <div>
      {fields.map((field, index) => (
        <Card key={index} size="small" className="mb-2">
          <Space direction="vertical" style={{ width: '100%' }}>
            <Input
              placeholder="Field Key"
              value={field.key}
              onChange={e => updateField(index, { key: e.target.value })}
            />
            <Input
              placeholder="Field Label"
              value={field.label}
              onChange={e => updateField(index, { label: e.target.value })}
            />
            <Select
              value={field.type}
              onChange={type => updateField(index, { type })}
              options={[
                { label: 'Text', value: 'text' },
                { label: 'Number', value: 'number' },
                { label: 'Select', value: 'select' },
                { label: 'Checkbox', value: 'checkbox' },
              ]}
            />
            <Checkbox
              checked={field.required}
              onChange={e => updateField(index, { required: e.target.checked })}
            >
              Required
            </Checkbox>
            <Button
              danger
              size="small"
              icon={<DeleteOutlined />}
              onClick={() => removeField(index)}
            >
              Remove
            </Button>
          </Space>
        </Card>
      ))}

      <Button
        type="dashed"
        icon={<PlusOutlined />}
        onClick={addField}
        block
      >
        Add Field
      </Button>
    </div>
  );
};
```

---

## Impact on Workflow

### 1. **Agent State Changes**

**Current:**
```python
state = {
    "messages": [HumanMessage(content=user_input)],
    "agent_config": {...},
    ...
}
```

**Enhanced:**
```python
state = {
    "messages": [HumanMessage(content=processed_message)],
    "agent_config": {...},
    "raw_input": original_user_input,
    "processed_input": {
        "mode": "json",
        "data": {...validated_data...},
    },
    "input_metadata": {
        "mode": "json",
        "timestamp": "2025-11-30T...",
        "validation_passed": true,
    },
    ...
}
```

### 2. **API Endpoint Changes**

**Current Execution Request:**
```json
POST /api/v1/execute/{agentId}
{
  "input": "What is the weather today?"
}
```

**Enhanced (supports all modes):**
```json
// Chat mode
POST /api/v1/execute/{agentId}
{
  "input": "What is the weather today?",
  "mode": "chat"
}

// JSON mode
POST /api/v1/execute/{agentId}
{
  "input": {
    "city": "San Francisco",
    "date": "2025-11-30",
    "units": "celsius"
  },
  "mode": "json"
}

// Form mode
POST /api/v1/execute/{agentId}
{
  "input": {
    "name": "John Doe",
    "email": "john@example.com",
    "age": 30
  },
  "mode": "form"
}
```

### 3. **Downstream Node Access**

All subsequent nodes can access:
```python
# Access original input
raw_input = state["raw_input"]

# Access validated/processed input
processed_input = state["processed_input"]

# Access metadata
input_mode = state["input_metadata"]["mode"]
```

### 4. **Testing Interface Update**

The AgentPlayground needs to adapt:
- Mode selector (Chat/JSON/Form)
- Dynamic input UI based on mode
- JSON editor for JSON mode
- Form builder for form mode
- Validation feedback

---

## Migration Strategy

### Phase 1: Backend Foundation (Week 1)
1. Update `AgentState` TypedDict to include `raw_input`, `processed_input`, `input_metadata`
2. Implement `InputNodeHandler` class with mode processing
3. Add JSON schema validation library
4. Update execution endpoint to accept mode parameter
5. Write unit tests for each mode

### Phase 2: Frontend UI (Week 1-2)
1. Update PropertyPanel with INPUT mode configuration
2. Create FormFieldBuilder component
3. Add JSON schema editor (consider Monaco editor)
4. Update AgentPlayground to support different input modes
5. Add input validation UI feedback

### Phase 3: Testing & Refinement (Week 2)
1. End-to-end testing with all three modes
2. Error handling and validation messages
3. Documentation updates
4. Migration guide for existing workflows

### Phase 4: Advanced Features (Week 3)
1. Input transformation functions
2. Conditional field logic for forms
3. Chat history management
4. Input preprocessing hooks

---

## Backward Compatibility

### Handling Existing Workflows

**Strategy:**
- Workflows without `config.mode` default to `"chat"` mode
- Existing string inputs are treated as chat messages
- No breaking changes to execution API (mode is optional)

**Migration Path:**
```typescript
// Auto-migration function
function migrateInputNode(node: Node): Node {
  if (node.data.type === 'INPUT' && !node.data.config?.mode) {
    return {
      ...node,
      data: {
        ...node.data,
        config: {
          mode: 'chat',
          chatConfig: {
            systemMessage: '',
            includeHistory: false,
          },
        },
      },
    };
  }
  return node;
}
```

---

## Use Case Examples

### Example 1: Customer Support Bot (Chat Mode)
```typescript
{
  mode: 'chat',
  chatConfig: {
    systemMessage: 'You are a friendly customer support agent for TechCorp.',
    includeHistory: true,
    maxHistoryMessages: 10,
  }
}
```

### Example 2: Order Processing API (JSON Mode)
```typescript
{
  mode: 'json',
  jsonConfig: {
    schema: {
      type: 'object',
      properties: {
        orderId: { type: 'string', pattern: '^ORD-\\d{6}$' },
        items: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              productId: { type: 'string' },
              quantity: { type: 'number', minimum: 1 }
            }
          }
        },
        totalAmount: { type: 'number', minimum: 0 }
      },
      required: ['orderId', 'items', 'totalAmount']
    },
    validateOnInput: true,
    coerceTypes: true
  }
}
```

### Example 3: Survey Collection (Form Mode)
```typescript
{
  mode: 'form',
  formConfig: {
    fields: [
      {
        key: 'name',
        label: 'Full Name',
        type: 'text',
        required: true,
        validation: { minLength: 2, maxLength: 100 }
      },
      {
        key: 'email',
        label: 'Email Address',
        type: 'text',
        required: true,
        validation: {
          pattern: '^[^@]+@[^@]+\\.[^@]+$',
          customMessage: 'Please enter a valid email'
        }
      },
      {
        key: 'satisfaction',
        label: 'How satisfied are you?',
        type: 'select',
        required: true,
        options: [
          { label: 'Very Satisfied', value: 5 },
          { label: 'Satisfied', value: 4 },
          { label: 'Neutral', value: 3 },
          { label: 'Dissatisfied', value: 2 },
          { label: 'Very Dissatisfied', value: 1 }
        ]
      }
    ]
  }
}
```

---

## Benefits

### For Users
1. **Flexibility**: Choose the right input mode for the use case
2. **Validation**: Catch errors early with schema validation
3. **Type Safety**: Ensure downstream nodes receive correct data types
4. **Reusability**: Define input contracts for agent templates
5. **Documentation**: Schema serves as self-documentation

### For Platform
1. **Standardization**: Consistent input handling across all agents
2. **Debugging**: Better error messages and validation feedback
3. **Testing**: Easier to create test cases with defined schemas
4. **Integration**: Better API integration capabilities
5. **Marketplace**: Templates can specify required input formats

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Breaking Changes** | Existing workflows fail | Default to chat mode, comprehensive migration guide |
| **Performance** | Validation overhead | Make validation optional, optimize schema validation |
| **Complexity** | Steep learning curve | Provide templates, good defaults, inline help |
| **UI Clutter** | Property panel becomes overwhelming | Collapsible sections, mode-specific views |
| **Schema Errors** | Invalid schemas break workflows | Schema validation tool, examples, preset schemas |

---

## Success Metrics

1. **Adoption Rate**: % of new workflows using enhanced INPUT modes
2. **Error Reduction**: Fewer execution failures due to input validation
3. **User Satisfaction**: Feedback scores on INPUT configuration UX
4. **Template Usage**: Number of templates leveraging different modes
5. **API Integration**: Number of JSON mode workflows created

---

## Next Steps

### For Review & Approval
1. **Review this proposal** - Validate approach and scope
2. **Prioritize modes** - Should we implement all three modes or start with chat + JSON?
3. **UI/UX Review** - Validate property panel mockups
4. **Timeline Approval** - Confirm phased implementation plan
5. **Dependencies** - Any prerequisites or blockers?

### Questions for Discussion
1. Should we support hybrid modes (e.g., chat with structured metadata)?
2. Do we need input preprocessing/transformation capabilities in v1?
3. Should form mode generate a visual form UI for end-users?
4. Do we need versioning for input schemas?
5. Should we provide a schema marketplace/library?

---

## References

- **n8n Chat Trigger**: Inspiration for conversational input handling
- **JSON Schema**: https://json-schema.org/
- **LangGraph State Management**: https://langchain-ai.github.io/langgraph/
- **React Hook Form**: Form validation patterns
- **Pydantic**: Python data validation

---

**Document Version**: 1.0
**Created**: 2025-11-30
**Author**: Claude (AgentStudio Analysis)
**Status**: Awaiting Review
