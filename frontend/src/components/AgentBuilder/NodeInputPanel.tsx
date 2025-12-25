import { Card, Tag, Tooltip, Space, Typography } from 'antd';
import { InfoCircleOutlined, CopyOutlined } from '@ant-design/icons';
import type { WorkflowNode } from '../../types/workflow';
import { NODE_SCHEMAS, type NodeField } from '../../types/nodeSchemas';

const { Text } = Typography;

interface NodeInputPanelProps {
  currentNode: WorkflowNode;
  upstreamNodes: WorkflowNode[]; // Nodes that come before this one
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
