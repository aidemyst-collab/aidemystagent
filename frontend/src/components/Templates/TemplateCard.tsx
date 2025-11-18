import React from 'react';
import { Card, Button, Tag, Space } from 'antd';
import { RocketOutlined, EyeOutlined } from '@ant-design/icons';

interface TemplateCardProps {
  id: string;
  name: string;
  description: string;
  category: string;
  tags: string[];
  onClone: (id: string) => void;
  onPreview: (id: string) => void;
}

export const TemplateCard: React.FC<TemplateCardProps> = ({
  id,
  name,
  description,
  category,
  tags,
  onClone,
  onPreview,
}) => {
  return (
    <Card
      hoverable
      className="h-full"
      actions={[
        <Button
          key="preview"
          type="text"
          icon={<EyeOutlined />}
          onClick={() => onPreview(id)}
        >
          Preview
        </Button>,
        <Button
          key="clone"
          type="primary"
          icon={<RocketOutlined />}
          onClick={() => onClone(id)}
        >
          Use Template
        </Button>,
      ]}
    >
      <Card.Meta
        title={<div className="text-lg font-semibold">{name}</div>}
        description={
          <Space direction="vertical" className="w-full">
            <p className="text-gray-600 mb-3">{description}</p>
            <div>
              <Tag color="blue">{category}</Tag>
              {tags.map((tag) => (
                <Tag key={tag}>{tag}</Tag>
              ))}
            </div>
          </Space>
        }
      />
    </Card>
  );
};
