import { Card, Tag, Button, Input, Select, Space, Typography, Tooltip } from 'antd';
import { PlusOutlined, DeleteOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { useState } from 'react';
import type { WorkflowNode } from '../../types/workflow';
import { NODE_SCHEMAS, type NodeField } from '../../types/nodeSchemas';

const { Text } = Typography;

interface NodeOutputPanelProps {
  currentNode: WorkflowNode;
  onUpdateCustomFields: (fields: NodeField[]) => void;
}

export const NodeOutputPanel = ({
  currentNode,
  onUpdateCustomFields
}: NodeOutputPanelProps) => {
  const schema = NODE_SCHEMAS[currentNode.data.type];
  const [customFields, setCustomFields] = useState<NodeField[]>(
    (currentNode.data.config as any)?.customOutputFields || []
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
          💡 Reference as: <Text code>{`{{${currentNode.id}.field_name}}`}</Text>
        </Text>
      </div>
    </Card>
  );
};
