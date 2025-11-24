import { Card, Tag, Button, Typography, Popconfirm } from 'antd';
import {
  ToolOutlined,
  PlayCircleOutlined,
  InfoCircleOutlined,
  EditOutlined,
  DeleteOutlined,
} from '@ant-design/icons';

const { Text, Paragraph } = Typography;

interface ToolCardProps {
  name: string;
  description: string;
  category: string;
  onTest?: () => void;
  onDetails?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
}

export const ToolCard = ({ name, description, category, onTest, onDetails, onEdit, onDelete }: ToolCardProps) => {
  const getCategoryColor = (cat: string) => {
    switch (cat.toLowerCase()) {
      case 'built-in':
        return 'blue';
      case 'api integration':
        return 'green';
      case 'custom':
        return 'purple';
      case 'mcp':
        return 'orange';
      default:
        return 'default';
    }
  };

  const actions = [
    <Button
      key="test"
      type="text"
      icon={<PlayCircleOutlined />}
      onClick={onTest}
    >
      Test
    </Button>,
    <Button
      key="details"
      type="text"
      icon={<InfoCircleOutlined />}
      onClick={onDetails}
    >
      Details
    </Button>,
  ];

  // Add edit/delete actions for custom tools
  if (onEdit) {
    actions.push(
      <Button
        key="edit"
        type="text"
        icon={<EditOutlined />}
        onClick={onEdit}
      >
        Edit
      </Button>
    );
  }

  if (onDelete) {
    actions.push(
      <Popconfirm
        key="delete"
        title="Delete this tool?"
        description="This action cannot be undone."
        onConfirm={onDelete}
        okText="Yes"
        cancelText="No"
        okButtonProps={{ danger: true }}
      >
        <Button
          type="text"
          danger
          icon={<DeleteOutlined />}
        >
          Delete
        </Button>
      </Popconfirm>
    );
  }

  return (
    <Card
      hoverable
      className="h-full"
      actions={actions}
    >
      <div className="flex items-start gap-3">
        <div className="text-2xl text-blue-500">
          <ToolOutlined />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Text strong className="text-base">
              {name}
            </Text>
            <Tag color={getCategoryColor(category)}>{category}</Tag>
          </div>
          <Paragraph
            type="secondary"
            ellipsis={{ rows: 2 }}
            style={{ marginBottom: 0 }}
          >
            {description}
          </Paragraph>
        </div>
      </div>
    </Card>
  );
};
