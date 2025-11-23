import { Card, Typography } from 'antd';
import {
  LoginOutlined,
  RobotOutlined,
  DatabaseOutlined,
  BranchesOutlined,
  ToolOutlined,
  ExportOutlined,
  ApartmentOutlined,
} from '@ant-design/icons';
import type { NodeType } from '../../types/agent';

const { Title, Text } = Typography;

interface NodeDefinition {
  type: NodeType;
  label: string;
  icon: React.ReactNode;
  color: string;
  description: string;
}

const nodeDefinitions: NodeDefinition[] = [
  {
    type: 'INPUT',
    label: 'Input',
    icon: <LoginOutlined />,
    color: '#52c41a',
    description: 'Entry point for user requests',
  },
  {
    type: 'LLM_AGENT',
    label: 'LLM Agent',
    icon: <RobotOutlined />,
    color: '#1890ff',
    description: 'Core language model agent',
  },
  {
    type: 'RAG_RETRIEVER',
    label: 'RAG Retriever',
    icon: <DatabaseOutlined />,
    color: '#722ed1',
    description: 'Retrieve knowledge from RAG system',
  },
  {
    type: 'DECISION',
    label: 'Decision',
    icon: <BranchesOutlined />,
    color: '#fa8c16',
    description: 'Conditional logic and routing',
  },
  {
    type: 'TOOL',
    label: 'Tool',
    icon: <ToolOutlined />,
    color: '#13c2c2',
    description: 'Execute specific tools',
  },
  {
    type: 'OUTPUT',
    label: 'Output',
    icon: <ExportOutlined />,
    color: '#f5222d',
    description: 'Final response formatting',
  },
  {
    type: 'SUBGRAPH',
    label: 'Subgraph',
    icon: <ApartmentOutlined />,
    color: '#eb2f96',
    description: 'Nested agent workflow',
  },
];

export const NodeLibrary = () => {
  const onDragStart = (event: React.DragEvent, nodeType: NodeType, label: string) => {
    event.dataTransfer.setData('application/reactflow', JSON.stringify({ nodeType, label }));
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className="p-4 bg-gray-50 h-full overflow-auto">
      <Title level={5}>Node Library</Title>
      <Text type="secondary" className="block mb-4">
        Drag nodes to the canvas
      </Text>

      <div className="space-y-2">
        {nodeDefinitions.map((node) => (
          <Card
            key={node.type}
            size="small"
            draggable
            onDragStart={(e) => onDragStart(e, node.type, node.label)}
            className="cursor-move hover:shadow-md transition-shadow"
            style={{ borderLeft: `3px solid ${node.color}` }}
          >
            <div className="flex items-center gap-2">
              <div style={{ color: node.color, fontSize: 18 }}>{node.icon}</div>
              <div>
                <div className="font-medium">{node.label}</div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {node.description}
                </Text>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};
