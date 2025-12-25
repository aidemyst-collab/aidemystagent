# Node Input/Output Visibility & Custom Properties

## Overview
Enhance the workflow builder UI to show users:
- What input data each node receives (from upstream nodes)
- What output data each node produces (available to downstream nodes)
- Available template variables they can reference
- Ability to add custom output fields/properties

---

## Current Problem

**When users configure nodes, they can't see:**
1. What data is available from previous nodes
2. What fields they can reference in templates (e.g., `{{input-1.message}}`)
3. What output this node will produce for downstream nodes
4. How to add custom fields to node outputs

---

## Proposed Solution

### 1. Add Input/Output Schema Panels to PropertyPanel

For each node type, show:
- **Input Schema**: What data this node receives
- **Output Schema**: What data this node produces
- **Available References**: Template variables from upstream nodes

### 2. Visual Design

```
┌─────────────────────────────────────┐
│ Properties - LLM Agent Node         │
├─────────────────────────────────────┤
│                                     │
│ ┌─ INPUT DATA ───────────────────┐ │
│ │ From: input-1 (User Input)     │ │
│ │ Available fields:              │ │
│ │  • message: string             │ │
│ │  • user_id: string             │ │
│ │  • timestamp: string           │ │
│ │                                │ │
│ │ [Click to insert template]     │ │
│ └────────────────────────────────┘ │
│                                     │
│ Label: [Main Agent________]         │
│                                     │
│ System Prompt:                      │
│ ┌─────────────────────────────────┐ │
│ │ You are helping                 │ │
│ │ {{input-1.user_id}}             │ │
│ │ [💡 Insert: input-1.message]    │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─ OUTPUT DATA ──────────────────┐ │
│ │ This node will produce:        │ │
│ │  • response: string            │ │
│ │  • tokens: object              │ │
│ │  • cost: number                │ │
│ │                                │ │
│ │ [+ Add Custom Output Field]    │ │
│ └────────────────────────────────┘ │
└─────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Node Schema Definitions

**File**: `frontend/src/types/nodeSchemas.ts` (new file)

```typescript
export interface NodeField {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'object' | 'array';
  description?: string;
  example?: any;
  required?: boolean;
}

export interface NodeSchema {
  inputs: NodeField[];
  outputs: NodeField[];
  customizable: boolean; // Can user add custom fields?
}

// Schema definitions for each node type
export const NODE_SCHEMAS: Record<string, NodeSchema> = {
  INPUT: {
    inputs: [],
    outputs: [
      { name: 'message', type: 'string', description: 'User input message', required: true },
      { name: 'mode', type: 'string', description: 'Input mode (chat/json/form)' },
      { name: 'timestamp', type: 'string', description: 'Input timestamp' },
      { name: 'user_id', type: 'string', description: 'User ID (if provided)' },
    ],
    customizable: true,
  },

  LLM_AGENT: {
    inputs: [
      { name: 'message', type: 'string', description: 'Input message or prompt' },
      { name: 'context', type: 'object', description: 'Additional context data' },
    ],
    outputs: [
      { name: 'response', type: 'string', description: 'LLM generated response', required: true },
      { name: 'tokens', type: 'object', description: 'Token usage stats' },
      { name: 'cost', type: 'number', description: 'API call cost' },
      { name: 'model', type: 'string', description: 'Model used' },
    ],
    customizable: false,
  },

  TOOL: {
    inputs: [
      { name: 'arguments', type: 'object', description: 'Tool input arguments' },
    ],
    outputs: [
      { name: 'result', type: 'object', description: 'Tool execution result', required: true },
      { name: 'success', type: 'boolean', description: 'Whether tool succeeded' },
      { name: 'error', type: 'string', description: 'Error message if failed' },
    ],
    customizable: true,
  },

  OUTPUT: {
    inputs: [
      { name: 'data', type: 'object', description: 'Data to format as output' },
    ],
    outputs: [
      { name: 'output', type: 'string', description: 'Final formatted output' },
    ],
    customizable: true,
  },

  MEMORY: {
    inputs: [
      { name: 'session_id', type: 'string', description: 'Session identifier' },
      { name: 'message', type: 'string', description: 'Current message' },
    ],
    outputs: [
      { name: 'chat_history', type: 'array', description: 'Previous conversation messages' },
      { name: 'context', type: 'object', description: 'Memory context' },
    ],
    customizable: false,
  },

  RAG_RETRIEVER: {
    inputs: [
      { name: 'query', type: 'string', description: 'Search query' },
    ],
    outputs: [
      { name: 'chunks', type: 'array', description: 'Retrieved document chunks' },
      { name: 'context', type: 'string', description: 'Formatted RAG context' },
      { name: 'scores', type: 'array', description: 'Relevance scores' },
    ],
    customizable: false,
  },
};
```

### Phase 2: Input Schema Component

**File**: `frontend/src/components/AgentBuilder/NodeInputPanel.tsx` (new file)

```typescript
import { Card, Tag, Tooltip, Button, Typography, Space } from 'antd';
import { InfoCircleOutlined, CopyOutlined } from '@ant-design/icons';
import type { Node } from '@xyflow/react';
import { NODE_SCHEMAS, type NodeField } from '../../types/nodeSchemas';

const { Text } = Typography;

interface NodeInputPanelProps {
  currentNode: Node;
  upstreamNodes: Node[]; // Nodes that come before this one
  onInsertTemplate: (template: string) => void;
}

export const NodeInputPanel = ({
  currentNode,
  upstreamNodes,
  onInsertTemplate
}: NodeInputPanelProps) => {
  // Get available fields from upstream nodes
  const availableFields = upstreamNodes.flatMap(node => {
    const schema = NODE_SCHEMAS[node.data.type];
    if (!schema) return [];

    return schema.outputs.map(field => ({
      nodeId: node.id,
      nodeLabel: node.data.label || node.data.type,
      ...field
    }));
  });

  const handleCopyTemplate = (nodeId: string, fieldName: string) => {
    const template = `{{${nodeId}.${fieldName}}}`;
    navigator.clipboard.writeText(template);
    onInsertTemplate(template);
  };

  if (availableFields.length === 0) {
    return (
      <Card size="small" title="Input Data" className="mb-3">
        <Text type="secondary" style={{ fontSize: 12 }}>
          No upstream nodes. This is the starting node.
        </Text>
      </Card>
    );
  }

  return (
    <Card
      size="small"
      title={
        <Space>
          <span>Input Data</span>
          <Tag color="blue">{availableFields.length} fields available</Tag>
        </Space>
      }
      className="mb-3"
    >
      <div className="space-y-2">
        {upstreamNodes.map(node => {
          const schema = NODE_SCHEMAS[node.data.type];
          if (!schema) return null;

          return (
            <div key={node.id} className="mb-3">
              <div className="flex items-center justify-between mb-1">
                <Text strong style={{ fontSize: 12 }}>
                  From: {node.data.label || node.id}
                </Text>
                <Tag color="green" style={{ fontSize: 10 }}>
                  {node.data.type}
                </Tag>
              </div>

              <div className="pl-2 border-l-2 border-blue-200">
                {schema.outputs.map(field => (
                  <div
                    key={field.name}
                    className="flex items-center justify-between py-1 hover:bg-gray-50 px-2 rounded cursor-pointer"
                    onClick={() => handleCopyTemplate(node.id, field.name)}
                  >
                    <Space size={4}>
                      <Text code style={{ fontSize: 11 }}>
                        {field.name}
                      </Text>
                      <Tag color="default" style={{ fontSize: 10 }}>
                        {field.type}
                      </Tag>
                      {field.description && (
                        <Tooltip title={field.description}>
                          <InfoCircleOutlined style={{ fontSize: 10, color: '#888' }} />
                        </Tooltip>
                      )}
                    </Space>
                    <Tooltip title={`Click to copy {{${node.id}.${field.name}}}`}>
                      <CopyOutlined style={{ fontSize: 11, color: '#1890ff' }} />
                    </Tooltip>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-3 pt-2 border-t border-gray-200">
        <Text type="secondary" style={{ fontSize: 11 }}>
          💡 Click any field to copy template syntax
        </Text>
      </div>
    </Card>
  );
};
```

### Phase 3: Output Schema Component

**File**: `frontend/src/components/AgentBuilder/NodeOutputPanel.tsx` (new file)

```typescript
import { Card, Tag, Button, Input, Select, Space, Typography, Tooltip } from 'antd';
import { PlusOutlined, DeleteOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { useState } from 'react';
import type { Node } from '@xyflow/react';
import { NODE_SCHEMAS, type NodeField } from '../../types/nodeSchemas';

const { Text } = Typography;

interface NodeOutputPanelProps {
  currentNode: Node;
  onUpdateCustomFields: (fields: NodeField[]) => void;
}

export const NodeOutputPanel = ({
  currentNode,
  onUpdateCustomFields
}: NodeOutputPanelProps) => {
  const schema = NODE_SCHEMAS[currentNode.data.type];
  const [customFields, setCustomFields] = useState<NodeField[]>(
    currentNode.data.config?.customOutputFields || []
  );

  if (!schema) return null;

  const handleAddCustomField = () => {
    const newField: NodeField = {
      name: `custom_field_${customFields.length + 1}`,
      type: 'string',
      description: 'Custom output field',
    };
    const updated = [...customFields, newField];
    setCustomFields(updated);
    onUpdateCustomFields(updated);
  };

  const handleRemoveCustomField = (index: number) => {
    const updated = customFields.filter((_, i) => i !== index);
    setCustomFields(updated);
    onUpdateCustomFields(updated);
  };

  const handleUpdateCustomField = (index: number, updates: Partial<NodeField>) => {
    const updated = [...customFields];
    updated[index] = { ...updated[index], ...updates };
    setCustomFields(updated);
    onUpdateCustomFields(updated);
  };

  const allFields = [...schema.outputs, ...customFields];

  return (
    <Card
      size="small"
      title={
        <Space>
          <span>Output Data</span>
          <Tag color="purple">{allFields.length} fields</Tag>
        </Space>
      }
      className="mb-3"
    >
      <Text type="secondary" style={{ fontSize: 11, display: 'block', marginBottom: 8 }}>
        Downstream nodes can reference these fields using templates
      </Text>

      {/* Built-in Output Fields */}
      <div className="space-y-1 mb-3">
        {schema.outputs.map(field => (
          <div
            key={field.name}
            className="flex items-center justify-between py-1 px-2 bg-blue-50 rounded"
          >
            <Space size={4}>
              <Text code style={{ fontSize: 11 }}>
                {field.name}
              </Text>
              <Tag color="blue" style={{ fontSize: 10 }}>
                {field.type}
              </Tag>
              {field.required && (
                <Tag color="red" style={{ fontSize: 10 }}>
                  required
                </Tag>
              )}
              {field.description && (
                <Tooltip title={field.description}>
                  <InfoCircleOutlined style={{ fontSize: 10, color: '#888' }} />
                </Tooltip>
              )}
            </Space>
          </div>
        ))}
      </div>

      {/* Custom Output Fields */}
      {schema.customizable && (
        <>
          <div className="border-t border-gray-200 pt-2 mt-2">
            <Text strong style={{ fontSize: 12 }}>
              Custom Fields
            </Text>
          </div>

          {customFields.map((field, index) => (
            <div key={index} className="mt-2 p-2 border border-gray-200 rounded">
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                <Input
                  size="small"
                  placeholder="Field name"
                  value={field.name}
                  onChange={(e) => handleUpdateCustomField(index, { name: e.target.value })}
                  prefix={<Text code style={{ fontSize: 10 }}>name:</Text>}
                />
                <Select
                  size="small"
                  style={{ width: '100%' }}
                  value={field.type}
                  onChange={(type) => handleUpdateCustomField(index, { type })}
                  options={[
                    { label: 'String', value: 'string' },
                    { label: 'Number', value: 'number' },
                    { label: 'Boolean', value: 'boolean' },
                    { label: 'Object', value: 'object' },
                    { label: 'Array', value: 'array' },
                  ]}
                />
                <Input
                  size="small"
                  placeholder="Description (optional)"
                  value={field.description}
                  onChange={(e) => handleUpdateCustomField(index, { description: e.target.value })}
                />
                <Button
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                  onClick={() => handleRemoveCustomField(index)}
                  block
                >
                  Remove Field
                </Button>
              </Space>
            </div>
          ))}

          <Button
            size="small"
            type="dashed"
            icon={<PlusOutlined />}
            onClick={handleAddCustomField}
            block
            className="mt-2"
          >
            Add Custom Output Field
          </Button>
        </>
      )}

      <div className="mt-3 pt-2 border-t border-gray-200">
        <Text type="secondary" style={{ fontSize: 11 }}>
          💡 Reference as: <Text code>{{`{{${currentNode.id}.field_name}}`}}</Text>
        </Text>
      </div>
    </Card>
  );
};
```

### Phase 4: Template Helper Component

**File**: `frontend/src/components/AgentBuilder/TemplateHelper.tsx` (new file)

```typescript
import { Card, Input, Button, Space, Typography, Popover, List } from 'antd';
import { ThunderboltOutlined } from '@ant-design/icons';
import { useState } from 'react';
import type { Node } from '@xyflow/react';

const { TextArea } = Input;
const { Text } = Typography;

interface TemplateHelperProps {
  value: string;
  onChange: (value: string) => void;
  availableNodes: Node[];
  placeholder?: string;
  rows?: number;
}

export const TemplateHelper = ({
  value,
  onChange,
  availableNodes,
  placeholder,
  rows = 4
}: TemplateHelperProps) => {
  const [cursorPosition, setCursorPosition] = useState(0);

  const insertTemplate = (template: string) => {
    const newValue =
      value.substring(0, cursorPosition) +
      template +
      value.substring(cursorPosition);
    onChange(newValue);
  };

  const templateMenu = (
    <div style={{ maxWidth: 300, maxHeight: 400, overflow: 'auto' }}>
      <List
        size="small"
        dataSource={availableNodes}
        renderItem={(node) => (
          <List.Item key={node.id}>
            <div style={{ width: '100%' }}>
              <Text strong style={{ fontSize: 11 }}>
                {node.data.label || node.id}
              </Text>
              <div className="mt-1">
                <Button
                  size="small"
                  type="link"
                  onClick={() => insertTemplate(`{{${node.id}.response}}`)}
                  style={{ fontSize: 10, padding: 0 }}
                >
                  Insert {{`{{${node.id}.response}}`}}
                </Button>
              </div>
            </div>
          </List.Item>
        )}
      />
    </div>
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <Space size={4}>
          <Text type="secondary" style={{ fontSize: 11 }}>
            Use {{`{{node_id.field}}`}} to reference data
          </Text>
        </Space>
        <Popover
          content={templateMenu}
          title="Insert Template"
          trigger="click"
          placement="bottomRight"
        >
          <Button
            size="small"
            icon={<ThunderboltOutlined />}
            type="dashed"
          >
            Quick Insert
          </Button>
        </Popover>
      </div>
      <TextArea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onSelect={(e: any) => setCursorPosition(e.target.selectionStart)}
        placeholder={placeholder}
        rows={rows}
        style={{ fontFamily: 'monospace', fontSize: 12 }}
      />
    </div>
  );
};
```

### Phase 5: Update PropertyPanel

**File**: `frontend/src/components/AgentBuilder/PropertyPanel.tsx`

Add the new components:

```typescript
import { NodeInputPanel } from './NodeInputPanel';
import { NodeOutputPanel } from './NodeOutputPanel';
import { TemplateHelper } from './TemplateHelper';

// Inside the PropertyPanel component, add helper function:
const getUpstreamNodes = (currentNode: Node, allNodes: Node[], allEdges: Edge[]): Node[] => {
  // Find all edges that point to the current node
  const incomingEdges = allEdges.filter(edge => edge.target === currentNode.id);

  // Get the source nodes
  return incomingEdges
    .map(edge => allNodes.find(node => node.id === edge.source))
    .filter((node): node is Node => node !== undefined);
};

// In the render, add at the top (after the Card showing node info):
return (
  <div className="p-4 bg-gray-50 h-full overflow-auto">
    <Title level={5}>Properties</Title>
    <Card size="small" className="mb-4">
      <div className="text-sm text-gray-600">Node ID: {selectedNode.id}</div>
      <div className="text-sm text-gray-600">Type: {selectedNode.data.type}</div>
    </Card>

    {/* NEW: Input Data Panel */}
    <NodeInputPanel
      currentNode={selectedNode}
      upstreamNodes={getUpstreamNodes(selectedNode, allNodes, allEdges)}
      onInsertTemplate={(template) => {
        // Insert into currently focused field
        console.log('Insert template:', template);
      }}
    />

    {/* NEW: Output Data Panel */}
    <NodeOutputPanel
      currentNode={selectedNode}
      onUpdateCustomFields={(fields) => {
        onUpdate(selectedNode.id, {
          ...selectedNode.data,
          config: {
            ...selectedNode.data.config,
            customOutputFields: fields
          }
        });
      }}
    />

    <Form form={form} layout="vertical" onValuesChange={handleValueChange}>
      {/* Rest of existing form fields */}

      {/* Replace TextArea inputs with TemplateHelper where applicable */}
      {selectedNode.data.type === 'LLM_AGENT' && (
        <Form.Item name={['config', 'systemPrompt']} label="System Prompt">
          <TemplateHelper
            value={form.getFieldValue(['config', 'systemPrompt']) || ''}
            onChange={(value) => form.setFieldValue(['config', 'systemPrompt'], value)}
            availableNodes={getUpstreamNodes(selectedNode, allNodes, allEdges)}
            placeholder="Enter system prompt with templates like {{input-1.message}}"
            rows={4}
          />
        </Form.Item>
      )}
    </Form>
  </div>
);
```

---

## User Workflow Example

### Creating a Weather Workflow

1. **Add INPUT Node**
   ```
   Output Data visible:
   • message: string
   • user_id: string
   • timestamp: string
   [+ Add Custom Field] → User adds "city: string"
   ```

2. **Add LLM_AGENT Node**
   ```
   Input Data visible:
   From: INPUT Node
   • message: string  [Copy]
   • user_id: string  [Copy]
   • city: string     [Copy]

   System Prompt field shows:
   [Quick Insert ▼] button

   User types: "Extract city from: {{input-1.message}}"

   Output Data visible:
   • response: string
   • tokens: object
   • cost: number
   ```

3. **Add TOOL Node (Weather API)**
   ```
   Input Data visible:
   From: INPUT Node + LLM_AGENT Node

   Tool Arguments field shows template helper:
   {
     "city": "{{input-1.city}}",
     "units": "fahrenheit"
   }

   Output Data visible:
   • result: object
     - temperature: number
     - condition: string
   • success: boolean
   ```

4. **Add OUTPUT Node**
   ```
   Input Data visible:
   From all previous nodes

   Template field:
   "Weather in {{input-1.city}}: {{tool-1.result.temperature}}°F, {{tool-1.result.condition}}"
   ```

---

## Benefits

1. **Visibility**: Users see exactly what data flows between nodes
2. **Discovery**: Auto-suggest available fields when typing templates
3. **Validation**: Can validate template references against schema
4. **Flexibility**: Custom fields for advanced use cases
5. **Documentation**: Schema serves as inline documentation

---

## Next Steps

1. Implement Phase 1: Node schema definitions
2. Implement Phase 2: Input panel component
3. Implement Phase 3: Output panel component
4. Implement Phase 4: Template helper
5. Implement Phase 5: Integration with PropertyPanel
6. Add validation for template references
7. Add auto-complete in text fields

---

## Future Enhancements

- **Visual Data Flow**: Highlight data connections on canvas
- **Live Preview**: Show resolved template values during config
- **Schema Inference**: Automatically detect output schema from execution
- **Type Checking**: Validate type compatibility between nodes
- **Documentation Links**: Link to field documentation/examples
