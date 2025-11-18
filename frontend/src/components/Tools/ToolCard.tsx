import { Card, Tag, Button, Typography } from 'antd';
import {
  ToolOutlined,
  PlayCircleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';

const { Text, Paragraph } = Typography;

interface ToolCardProps {
  name: string;
  description: string;
  category: string;
  onTest?: () => void;
  onDetails?: () => void;
}

export const ToolCard = ({ name, description, category, onTest, onDetails }: ToolCardProps) => {
  const getCategoryColor = (cat: string) => {
    switch (cat.toLowerCase()) {
      case 'built-in':
        return 'blue';
      case 'api integration':
        return 'green';
      case 'custom':
        return 'purple';
      default:
        return 'default';
    }
  };

  return (
    <Card
      hoverable
      className="h-full"
      actions={[
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
      ]}
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
