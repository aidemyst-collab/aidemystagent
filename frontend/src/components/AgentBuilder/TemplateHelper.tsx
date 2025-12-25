import { Input, Button, Space, Typography, Popover, List } from 'antd';
import { ThunderboltOutlined } from '@ant-design/icons';
import { useState } from 'react';
import type { WorkflowNode } from '../../types/workflow';
import { NODE_SCHEMAS } from '../../types/nodeSchemas';

const { TextArea } = Input;
const { Text } = Typography;

interface TemplateHelperProps {
  value: string;
  onChange: (value: string) => void;
  availableNodes: WorkflowNode[];
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
        renderItem={(node) => {
          const schema = NODE_SCHEMAS[node.data.type];
          if (!schema) return null;

          return (
            <List.Item key={node.id}>
              <div style={{ width: '100%' }}>
                <Text strong style={{ fontSize: 11 }}>
                  {node.data.label || node.id}
                </Text>
                <div className="mt-1">
                  {schema.outputs.map(field => (
                    <Button
                      key={field.name}
                      size="small"
                      type="link"
                      onClick={() => insertTemplate(`{{${node.id}.${field.name}}}`)}
                      style={{ fontSize: 10, padding: 0, marginRight: 8 }}
                    >
                      {field.name}
                    </Button>
                  ))}
                </div>
              </div>
            </List.Item>
          );
        }}
      />
    </div>
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <Space size={4}>
          <Text type="secondary" style={{ fontSize: 11 }}>
            Use {`{{node_id.field}}`} to reference data
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
