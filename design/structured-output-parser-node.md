# Structured Output Parser Node Design

## Overview

Add a **STRUCTURED_OUTPUT_PARSER** node that parses LLM outputs into structured, validated formats. This node ensures AI agent responses follow a predefined schema, making outputs predictable and machine-readable.

**Inspired by:** [n8n Structured Output Parser](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.outputparserstructured/)

---

## Problem Statement

Current challenges with LLM outputs:
- **Inconsistent formats**: LLMs generate free-form text that varies between requests
- **No validation**: No guarantee that responses contain required fields
- **Parsing complexity**: Manual parsing of LLM outputs is error-prone
- **Type safety**: No type enforcement for extracted data
- **Integration issues**: Difficult to pass LLM outputs to downstream systems expecting structured data

---

## Use Cases

1. **Data Extraction**: Extract structured information from documents (names, dates, addresses)
2. **API Response Formatting**: Convert LLM analysis into JSON for API consumption
3. **Database Insertion**: Parse LLM outputs into database-ready records
4. **Form Filling**: Extract structured data to populate forms or templates
5. **Classification & Tagging**: Structure LLM categorization results
6. **Multi-field Extraction**: Extract multiple related fields (product name, price, description)
7. **Validation & Quality**: Ensure LLM outputs meet specific requirements
8. **Workflow Routing**: Use structured output for conditional routing decisions

---

## Node Type Definition

### Node Type: `STRUCTURED_OUTPUT_PARSER`

**Category:** Processing / Transformation
**Icon:** 🔍 (Magnifying glass or structure icon)
**Color:** Purple (#9333EA)
**Position:** Between LLM_AGENT and OUTPUT/DECISION nodes

---

## How It Works

### Workflow Integration

```
INPUT → LLM_AGENT → STRUCTURED_OUTPUT_PARSER → OUTPUT
                                              ↓
                                         DECISION
                                              ↓
                                         TOOL
```

### Processing Flow

1. **Receive LLM output** from upstream LLM_AGENT node
2. **Apply schema** to extract and validate fields
3. **Parse response** using configured parser type
4. **Validate data** against schema rules
5. **Transform output** to structured format
6. **Pass to next node** with validated, typed data

---

## Configuration Options

### 1. **Parser Type** (Required)
- **Type:** Select
- **Options:**
  - `json_schema` - JSON Schema validation (default)
  - `zod_schema` - Zod schema (TypeScript-style)
  - `field_extractor` - Simple field extraction
  - `key_value` - Key-value pair extraction
  - `structured_template` - Template-based parsing
- **Default:** `json_schema`
- **Description:** Method used to parse and validate output

### 2. **Schema Definition** (Required for json_schema, zod_schema)
- **Type:** Code Editor (JSON/TypeScript)
- **Description:** Schema defining the expected output structure
- **Supports:**
  - JSON Schema (Draft 7)
  - Zod schema syntax
  - Field definitions with types
- **Example (JSON Schema):**
  ```json
  {
    "type": "object",
    "properties": {
      "name": {
        "type": "string",
        "description": "Product name"
      },
      "price": {
        "type": "number",
        "minimum": 0
      },
      "inStock": {
        "type": "boolean"
      },
      "tags": {
        "type": "array",
        "items": { "type": "string" }
      }
    },
    "required": ["name", "price"]
  }
  ```

### 3. **Fields to Extract** (Required for field_extractor)
- **Type:** Array of field definitions
- **Each field has:**
  - **Name:** Field identifier
  - **Type:** `string`, `number`, `boolean`, `array`, `object`, `date`
  - **Description:** What this field represents (helps LLM understand)
  - **Required:** Whether field must be present
  - **Default Value:** Value if field is missing
  - **Validation Rules:** Min/max, pattern, enum values

**Example:**
```typescript
[
  {
    name: "customer_name",
    type: "string",
    description: "Full name of the customer",
    required: true
  },
  {
    name: "order_total",
    type: "number",
    description: "Total order amount in USD",
    required: true,
    validation: { minimum: 0 }
  },
  {
    name: "order_items",
    type: "array",
    description: "List of items ordered",
    required: false,
    default: []
  }
]
```

### 4. **Parsing Strategy** (Required)
- **Type:** Select
- **Options:**
  - `strict` - Fail if schema doesn't match exactly
  - `lenient` - Best-effort parsing with defaults
  - `auto_fix` - Attempt to fix common issues (e.g., quoted numbers)
- **Default:** `lenient`
- **Description:** How to handle parsing errors

### 5. **Output Format** (Required)
- **Type:** Select
- **Options:**
  - `json` - JSON object (default)
  - `flattened` - Flat key-value object
  - `typed_array` - Array of typed objects
  - `custom` - Custom transformation
- **Default:** `json`

### 6. **Error Handling** (Required)
- **Type:** Select
- **Options:**
  - `fail` - Stop workflow on parsing error (default)
  - `pass_through` - Pass original text if parsing fails
  - `default_values` - Use default values for all fields
  - `retry_llm` - Send back to LLM with error feedback
- **Default:** `fail`

### 7. **Validation Rules** (Optional)
- **Type:** Object (per field)
- **Options:**
  - **String:** `minLength`, `maxLength`, `pattern`, `enum`
  - **Number:** `minimum`, `maximum`, `multipleOf`
  - **Array:** `minItems`, `maxItems`, `uniqueItems`
  - **Object:** `required`, `additionalProperties`
  - **Date:** `minDate`, `maxDate`, `format`

### 8. **Type Coercion** (Optional)
- **Type:** Boolean
- **Default:** `true`
- **Description:** Automatically convert types (e.g., "123" → 123)
- **Examples:**
  - `"true"` → `true`
  - `"42"` → `42`
  - `"2024-01-01"` → `Date object`

### 9. **Missing Field Behavior** (Optional)
- **Type:** Select
- **Options:**
  - `error` - Throw error for missing required fields
  - `null` - Set missing fields to null
  - `omit` - Don't include missing fields in output
  - `default` - Use default values
- **Default:** `error`

### 10. **LLM Guidance** (Optional)
- **Type:** Toggle + Text Area
- **Default:** `enabled`
- **Description:** Add schema instructions to LLM prompt
- **Auto-generates prompts like:**
  ```
  Please respond in the following JSON format:
  {
    "name": "string - Product name",
    "price": "number - Price in USD (minimum 0)",
    "inStock": "boolean - Whether product is available"
  }
  Ensure your response is valid JSON.
  ```

### 11. **Retry Configuration** (when error_handling = retry_llm)
- **Max Retries:** Number (default: 2, max: 5)
- **Retry Prompt Template:** Text template with error feedback
- **Example:**
  ```
  Your previous response was not in the correct format.
  Error: {{error_message}}
  Please try again following this exact schema: {{schema}}
  ```

---

## Input/Output Schema

### Input (from previous node)
```typescript
{
  // From LLM_AGENT or previous node
  response: string,           // Raw LLM output text
  metadata?: {
    model: string,
    tokens: number,
    timestamp: string
  }
}
```

### Output (to next node)
```typescript
{
  // Parsed and validated data
  parsed_data: {
    [key: string]: any       // Structured fields matching schema
  },

  // Original data
  original_response: string, // Raw LLM output (optional)

  // Metadata
  parsing_success: boolean,
  validation_errors: Array<{
    field: string,
    error: string,
    value: any
  }>,

  // Performance tracking
  parsing_time_ms: number,
  retry_count: number,

  // Schema info
  schema_version: string,
  fields_extracted: string[]
}
```

---

## Frontend Implementation

### Node Component (`StructuredOutputParserNode.tsx`)

**Location:** `frontend/src/components/AgentBuilder/nodes/StructuredOutputParserNode.tsx`

```typescript
import { CheckCircleOutlined } from '@ant-design/icons';
import { AuxiliaryNode } from './AuxiliaryNode';
import type { NodeProps } from '@xyflow/react';

export const StructuredOutputParserNode = (props: NodeProps) => {
  return (
    <AuxiliaryNode
      {...props}
      icon={<CheckCircleOutlined />}
      color="#9333EA"
    />
  );
};
```

**Export in index.ts:**
```typescript
// frontend/src/components/AgentBuilder/nodes/index.ts
export { StructuredOutputParserNode } from './StructuredOutputParserNode';
```

### Property Panel Configuration

**Location:** `frontend/src/components/AgentBuilder/PropertyPanel.tsx`

Add this case to the PropertyPanel component:

```typescript
{selectedNode.data.type === 'STRUCTURED_OUTPUT_PARSER' && (
  <>
    <Typography.Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 8 }}>
      Parse LLM outputs into structured, validated JSON format
    </Typography.Text>

    <Card size="small" title="Parser Configuration" style={{ marginBottom: 16 }}>
      <Form.Item
        name={['config', 'parserType']}
        label="Parser Type"
        initialValue="json_schema"
      >
        <Select>
          <Select.Option value="json_schema">JSON Schema</Select.Option>
          <Select.Option value="field_extractor">Field Extractor</Select.Option>
          <Select.Option value="key_value">Key-Value Pairs</Select.Option>
        </Select>
      </Form.Item>

      <Form.Item
        name={['config', 'strategy']}
        label="Parsing Strategy"
        initialValue="lenient"
      >
        <Select>
          <Select.Option value="strict">Strict - Fail if mismatch</Select.Option>
          <Select.Option value="lenient">Lenient - Best effort</Select.Option>
          <Select.Option value="auto_fix">Auto-fix - Attempt repairs</Select.Option>
        </Select>
      </Form.Item>
    </Card>

    <Card size="small" title="Schema Definition" style={{ marginBottom: 16 }}>
      <Form.Item
        name={['config', 'schema']}
        label="JSON Schema"
        tooltip="Define the expected output structure"
      >
        <TextArea
          rows={8}
          placeholder={`{
  "type": "object",
  "properties": {
    "name": { "type": "string" },
    "price": { "type": "number" }
  },
  "required": ["name"]
}`}
          style={{ fontFamily: 'monospace', fontSize: 12 }}
        />
      </Form.Item>
    </Card>

    <Card size="small" title="Error Handling" style={{ marginBottom: 16 }}>
      <Form.Item
        name={['config', 'errorHandling']}
        label="On Parse Error"
        initialValue="fail"
      >
        <Select>
          <Select.Option value="fail">Fail execution</Select.Option>
          <Select.Option value="pass_through">Pass original text</Select.Option>
          <Select.Option value="default_values">Use default values</Select.Option>
          <Select.Option value="retry_llm">Retry with LLM</Select.Option>
        </Select>
      </Form.Item>

      <Form.Item
        name={['config', 'typeCoercion']}
        valuePropName="checked"
        initialValue={true}
      >
        <Checkbox>Enable type coercion (e.g., "123" → 123)</Checkbox>
      </Form.Item>

      <Form.Item
        name={['config', 'llmGuidance']}
        valuePropName="checked"
        initialValue={true}
      >
        <Checkbox>Add schema instructions to LLM prompt</Checkbox>
      </Form.Item>
    </Card>
  </>
)}
```

---

## Node Schema Definition

**Location:** `frontend/src/types/nodeSchemas.ts`

Add to `NODE_SCHEMAS`:

```typescript
STRUCTURED_OUTPUT_PARSER: {
  inputs: [
    { name: 'response', type: 'string', description: 'LLM output text to parse', required: true },
  ],
  outputs: [
    { name: 'parsed_data', type: 'object', description: 'Structured parsed output', required: true },
    { name: 'parsing_success', type: 'boolean', description: 'Whether parsing succeeded' },
    { name: 'validation_errors', type: 'array', description: 'List of validation errors' },
    { name: 'fields_extracted', type: 'array', description: 'Names of extracted fields' },
  ],
  customizable: true,
},
```

---

## Backend Implementation

**Location:** `backend/app/services/langgraph_engine.py`

### StructuredOutputParser Class

```python
from typing import Dict, Any, List, Optional
import json
import re
from datetime import datetime
from jsonschema import validate, ValidationError as JSONSchemaError

class StructuredOutputParser:
    """Parse and validate LLM outputs against schemas."""

    def __init__(self, config: Dict[str, Any]):
        self.parser_type = config.get('parserType', 'json_schema')
        self.schema = config.get('schema', {})
        self.fields = config.get('fields', [])
        self.strategy = config.get('strategy', 'lenient')
        self.error_handling = config.get('errorHandling', 'fail')
        self.type_coercion = config.get('typeCoercion', True)
        self.output_format = config.get('outputFormat', 'json')

    def parse(self, llm_output: str) -> Dict[str, Any]:
        """Parse LLM output based on configuration."""
        try:
            # Step 1: Extract JSON from text
            parsed_json = self._extract_json(llm_output)

            # Step 2: Validate against schema
            if self.parser_type == 'json_schema':
                validated = self._validate_json_schema(parsed_json)
            elif self.parser_type == 'field_extractor':
                validated = self._extract_fields(parsed_json)
            else:
                validated = parsed_json

            # Step 3: Apply type coercion
            if self.type_coercion:
                validated = self._coerce_types(validated)

            # Step 4: Format output
            formatted = self._format_output(validated)

            return {
                'parsed_data': formatted,
                'original_response': llm_output,
                'parsing_success': True,
                'validation_errors': [],
                'fields_extracted': list(formatted.keys())
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
            return json.loads(json_match.group(1))

        # Look for JSON object anywhere in text
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))

        # If lenient, return empty dict
        if self.strategy == 'lenient':
            return {}

        raise ValueError("No JSON found in LLM output")

    def _validate_json_schema(self, data: Dict) -> Dict:
        """Validate data against JSON schema."""
        try:
            validate(instance=data, schema=self.schema)
            return data
        except JSONSchemaError as e:
            if self.strategy == 'strict':
                raise
            elif self.strategy == 'lenient':
                # Return what we have, fill missing with defaults
                return self._apply_defaults(data)
            else:  # auto_fix
                return self._auto_fix_schema(data, e)

    def _extract_fields(self, data: Dict) -> Dict:
        """Extract specific fields based on field definitions."""
        result = {}
        errors = []

        for field_def in self.fields:
            field_name = field_def['name']
            field_type = field_def.get('type', 'string')
            required = field_def.get('required', False)
            default = field_def.get('default')

            # Get value from data
            value = data.get(field_name)

            if value is None:
                if required and not default:
                    errors.append({
                        'field': field_name,
                        'error': 'Required field missing',
                        'value': None
                    })
                else:
                    value = default

            # Type validation and conversion
            try:
                value = self._convert_type(value, field_type)
                result[field_name] = value
            except ValueError as e:
                errors.append({
                    'field': field_name,
                    'error': str(e),
                    'value': value
                })

        if errors and self.strategy == 'strict':
            raise ValueError(f"Field extraction errors: {errors}")

        return result

    def _coerce_types(self, data: Dict) -> Dict:
        """Coerce values to correct types."""
        coerced = {}

        for key, value in data.items():
            # Get expected type from schema
            if self.parser_type == 'json_schema':
                expected_type = self.schema.get('properties', {}).get(key, {}).get('type')
            else:
                field_def = next((f for f in self.fields if f['name'] == key), None)
                expected_type = field_def.get('type') if field_def else None

            if expected_type:
                coerced[key] = self._convert_type(value, expected_type)
            else:
                coerced[key] = value

        return coerced

    def _convert_type(self, value: Any, target_type: str) -> Any:
        """Convert value to target type."""
        if value is None:
            return None

        converters = {
            'string': str,
            'number': float,
            'integer': int,
            'boolean': lambda v: v if isinstance(v, bool) else str(v).lower() in ('true', '1', 'yes'),
            'array': lambda v: v if isinstance(v, list) else [v],
        }

        converter = converters.get(target_type)
        if converter:
            return converter(value)

        return value

    def _format_output(self, data: Dict) -> Dict:
        """Format output based on configuration."""
        if self.output_format == 'json':
            return data
        elif self.output_format == 'flattened':
            return self._flatten_dict(data)
        else:
            return data

    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '.') -> Dict:
        """Flatten nested dictionary."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def _apply_defaults(self, data: Dict) -> Dict:
        """Apply default values for missing fields."""
        result = data.copy()

        if self.parser_type == 'json_schema':
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
                'validation_errors': [{'error': str(error)}]
            }
        elif self.error_handling == 'default_values':
            defaults = {}
            for field in self.fields:
                defaults[field['name']] = field.get('default')
            return {
                'parsed_data': defaults,
                'original_response': original,
                'parsing_success': False,
                'validation_errors': [{'error': str(error)}]
            }
        else:
            raise error


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
        "raw_output": llm_output[:500],  # First 500 chars
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
            "error": None if result["parsing_success"] else result.get("validation_errors"),
            "metadata": parser_config,
        })

        state["execution_path"].append("STRUCTURED_OUTPUT_PARSER")

        # Log success
        logger.info(f"Successfully parsed output: {len(result['fields_extracted'])} fields")

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
```

---

## LLM Prompt Enhancement

When **LLM Guidance** is enabled, automatically prepend schema instructions to the LLM prompt:

```python
def _enhance_llm_prompt_with_schema(prompt: str, parser_config: Dict) -> str:
    """Add schema instructions to LLM prompt."""

    if not parser_config.get('llmGuidance', True):
        return prompt

    schema = parser_config.get('schema', {})
    fields = parser_config.get('fields', [])

    # Generate schema description
    if schema:
        schema_description = json.dumps(schema, indent=2)
        instruction = f"""
Please respond in the following JSON format:
{schema_description}

Ensure your response is valid JSON matching this exact schema.

"""
    elif fields:
        field_descriptions = []
        for field in fields:
            req = "required" if field.get('required') else "optional"
            field_descriptions.append(
                f'  "{field["name"]}": {field["type"]} ({req}) - {field.get("description", "")}'
            )

        instruction = f"""
Please respond in JSON format with the following fields:
{{
{chr(10).join(field_descriptions)}
}}

Ensure your response is valid JSON.

"""
    else:
        return prompt

    return instruction + prompt
```

---

## Usage Examples

### Example 1: Product Information Extraction

**Configuration:**
```json
{
  "parserType": "json_schema",
  "schema": {
    "type": "object",
    "properties": {
      "product_name": { "type": "string" },
      "price": { "type": "number", "minimum": 0 },
      "availability": { "type": "boolean" },
      "categories": {
        "type": "array",
        "items": { "type": "string" }
      }
    },
    "required": ["product_name", "price"]
  },
  "strategy": "lenient",
  "errorHandling": "default_values"
}
```

**LLM Output:**
```
Based on the product page, here's what I found:

The iPhone 15 Pro is priced at $999 and is currently in stock.
It belongs to the Electronics and Smartphones categories.
```

**Parsed Output:**
```json
{
  "product_name": "iPhone 15 Pro",
  "price": 999,
  "availability": true,
  "categories": ["Electronics", "Smartphones"]
}
```

### Example 2: Customer Feedback Analysis

**Configuration:**
```json
{
  "parserType": "field_extractor",
  "fields": [
    {
      "name": "sentiment",
      "type": "string",
      "description": "Overall sentiment (positive/negative/neutral)",
      "required": true
    },
    {
      "name": "rating",
      "type": "number",
      "description": "Rating from 1-5",
      "required": true,
      "validation": { "minimum": 1, "maximum": 5 }
    },
    {
      "name": "issues",
      "type": "array",
      "description": "List of issues mentioned",
      "required": false,
      "default": []
    },
    {
      "name": "would_recommend",
      "type": "boolean",
      "description": "Would customer recommend",
      "required": false
    }
  ]
}
```

### Example 3: Form Data Extraction

**Configuration:**
```json
{
  "parserType": "json_schema",
  "schema": {
    "type": "object",
    "properties": {
      "full_name": { "type": "string", "minLength": 2 },
      "email": {
        "type": "string",
        "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
      },
      "phone": { "type": "string" },
      "preferred_contact": {
        "type": "string",
        "enum": ["email", "phone", "sms"]
      }
    },
    "required": ["full_name", "email"]
  },
  "typeCoercion": true,
  "errorHandling": "retry_llm"
}
```

---

## Validation & Testing

### Unit Tests

```python
# Test JSON extraction
def test_extract_json_from_text():
    parser = StructuredOutputParser({'parserType': 'json_schema'})
    text = """
    Here's the data you requested:
    ```json
    {"name": "Test", "value": 42}
    ```
    """
    result = parser._extract_json(text)
    assert result == {"name": "Test", "value": 42}

# Test type coercion
def test_type_coercion():
    parser = StructuredOutputParser({
        'parserType': 'json_schema',
        'typeCoercion': True,
        'schema': {
            'properties': {
                'age': {'type': 'number'},
                'active': {'type': 'boolean'}
            }
        }
    })
    data = {'age': '25', 'active': 'true'}
    result = parser._coerce_types(data)
    assert result['age'] == 25
    assert result['active'] is True

# Test error handling
def test_error_handling_pass_through():
    parser = StructuredOutputParser({
        'parserType': 'json_schema',
        'errorHandling': 'pass_through'
    })
    result = parser._handle_error("Invalid JSON", ValueError("Parse error"))
    assert result['parsing_success'] is False
    assert 'raw_text' in result['parsed_data']
```

---

## Performance Considerations

### Optimization Strategies

1. **Schema Caching**: Cache compiled schemas to avoid re-parsing
2. **Regex Optimization**: Pre-compile regex patterns for JSON extraction
3. **Parallel Validation**: Validate independent fields in parallel
4. **Lazy Loading**: Only load validation libraries when needed
5. **Result Caching**: Cache parsing results for identical inputs

### Expected Performance

- **Simple extraction**: < 10ms
- **JSON schema validation**: 20-50ms
- **Complex nested objects**: 50-100ms
- **With retry**: 2-10 seconds (depends on LLM)

---

## Error Handling

### Common Errors

1. **No JSON found**: LLM output doesn't contain JSON
   - **Solution**: Enable `llmGuidance`, use `lenient` strategy

2. **Schema mismatch**: Output doesn't match schema
   - **Solution**: Use `auto_fix` strategy, add default values

3. **Type conversion error**: Cannot convert value to target type
   - **Solution**: Enable `typeCoercion`, add validation rules

4. **Missing required fields**: Required fields not present
   - **Solution**: Use `retry_llm` or `default_values` error handling

### Error Messages

Provide clear, actionable error messages:
```json
{
  "error": "Schema validation failed",
  "field": "price",
  "expected": "number >= 0",
  "received": "-10",
  "suggestion": "Ensure the LLM outputs a positive number for price"
}
```

---

## Security Considerations

1. **Schema Injection**: Validate user-provided schemas
2. **DoS Prevention**: Limit schema complexity and nesting depth
3. **Regex Safety**: Prevent ReDoS attacks in pattern validation
4. **Output Size**: Limit maximum output size to prevent memory issues
5. **Sanitization**: Sanitize extracted data before database insertion

---

## Migration Path

### Phase 1: Basic Implementation
- JSON schema validation
- Field extractor mode
- Basic error handling

### Phase 2: Advanced Features
- LLM guidance with auto-prompting
- Retry mechanism with feedback
- Custom validation rules

### Phase 3: Enhancements
- Zod schema support
- AI-powered schema inference
- Performance optimizations

---

## Success Metrics

1. **Parsing Success Rate**: > 95% for well-defined schemas
2. **Performance**: < 100ms for most operations
3. **User Adoption**: Used in > 30% of workflows
4. **Error Recovery**: < 5% unrecoverable errors

---

## Documentation

### User Guide Sections

1. **Getting Started**: Basic schema setup
2. **Schema Definition**: How to write JSON schemas
3. **Field Extraction**: Using the field extractor
4. **Error Handling**: Dealing with parsing failures
5. **Best Practices**: Tips for reliable parsing
6. **Troubleshooting**: Common issues and solutions

### API Documentation

- Schema format reference
- Configuration options
- Input/output examples
- Error codes and messages

---

## Future Enhancements

1. **AI Schema Inference**: Automatically generate schemas from examples
2. **Multi-format Support**: Parse XML, YAML, CSV outputs
3. **Streaming Parsing**: Parse LLM streaming outputs in real-time
4. **Visual Schema Builder**: Drag-and-drop schema designer
5. **Schema Marketplace**: Share and reuse common schemas
6. **Analytics**: Track parsing success rates and common failures
7. **A/B Testing**: Test different schemas and strategies
8. **Schema Evolution**: Version and migrate schemas over time

---

## Appendix

### JSON Schema Resources
- [JSON Schema Documentation](https://json-schema.org/)
- [Understanding JSON Schema](https://json-schema.org/understanding-json-schema/)
- [Schema Validator Tool](https://www.jsonschemavalidator.net/)

### Related Nodes
- **LLM_AGENT**: Provides input to parser
- **DECISION**: Uses parsed output for routing
- **OUTPUT**: Formats parsed data for display
- **TOOL**: Uses structured data for API calls

---

**Document Version:** 1.0
**Last Updated:** 2025-12-06
**Status:** Design Complete - Ready for Implementation
