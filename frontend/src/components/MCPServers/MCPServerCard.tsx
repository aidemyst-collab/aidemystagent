import { Card, Tag, Typography, Space, Button, Tooltip, Popconfirm } from 'antd';
import {
  CloudServerOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  SearchOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import type { MCPServer } from '../../features/mcp-servers/mcpServerService';

const { Text, Paragraph } = Typography;

interface MCPServerCardProps {
  server: MCPServer;
  onTest: () => void;
  onDiscover: () => void;
  onEdit: () => void;
  onDelete: () => void;
  loading?: boolean;
}

const statusConfig = {
  active: {
    color: 'success',
    icon: <CheckCircleOutlined />,
    text: 'Active',
  },
  inactive: {
    color: 'default',
    icon: <CloseCircleOutlined />,
    text: 'Inactive',
  },
  error: {
    color: 'error',
    icon: <ExclamationCircleOutlined />,
    text: 'Error',
  },
};

const transportColors: Record<string, string> = {
  sse: 'blue',
  http: 'green',
  stdio: 'purple',
};

export const MCPServerCard = ({
  server,
  onTest,
  onDiscover,
  onEdit,
  onDelete,
  loading = false,
}: MCPServerCardProps) => {
  const status = statusConfig[server.status] || statusConfig.inactive;
  const toolCount = server.discovered_tools?.length || 0;
  const resourceCount = server.discovered_resources?.length || 0;
  const promptCount = server.discovered_prompts?.length || 0;

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString();
  };

  return (
    <Card
      hoverable
      className="h-full"
      styles={{
        body: { padding: '16px' },
      }}
      actions={[
        <Tooltip title="Test Connection" key="test">
          <Button
            type="text"
            icon={<PlayCircleOutlined />}
            onClick={onTest}
            loading={loading}
          />
        </Tooltip>,
        <Tooltip title="Discover Capabilities" key="discover">
          <Button
            type="text"
            icon={<SearchOutlined />}
            onClick={onDiscover}
            loading={loading}
          />
        </Tooltip>,
        <Tooltip title="Edit" key="edit">
          <Button type="text" icon={<EditOutlined />} onClick={onEdit} />
        </Tooltip>,
        <Popconfirm
          title="Delete this MCP server?"
          description="This action cannot be undone."
          onConfirm={onDelete}
          okText="Delete"
          cancelText="Cancel"
          okButtonProps={{ danger: true }}
          key="delete"
        >
          <Button type="text" danger icon={<DeleteOutlined />} />
        </Popconfirm>,
      ]}
    >
      <div className="flex flex-col gap-3">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <CloudServerOutlined style={{ fontSize: 20, color: '#6366f1' }} />
            <Text strong className="text-base">
              {server.name}
            </Text>
          </div>
          <Tag icon={status.icon} color={status.color as any}>
            {status.text}
          </Tag>
        </div>

        {/* Description */}
        {server.description && (
          <Paragraph
            type="secondary"
            ellipsis={{ rows: 2 }}
            className="mb-0 text-sm"
          >
            {server.description}
          </Paragraph>
        )}

        {/* Server URL */}
        <div>
          <Text type="secondary" className="text-xs">
            Server URL
          </Text>
          <Paragraph
            copyable={{ text: server.server_url }}
            ellipsis={{ rows: 1 }}
            className="mb-0 text-sm font-mono"
          >
            {server.server_url}
          </Paragraph>
        </div>

        {/* Transport Type */}
        <div className="flex items-center gap-2">
          <Text type="secondary" className="text-xs">
            Transport:
          </Text>
          <Tag color={transportColors[server.transport_type] || 'default'}>
            {server.transport_type.toUpperCase()}
          </Tag>
        </div>

        {/* Discovered Capabilities */}
        <div className="flex items-center gap-2 flex-wrap">
          <Text type="secondary" className="text-xs">
            Discovered:
          </Text>
          <Space size={4}>
            <Tooltip title="Tools">
              <Tag color="blue">{toolCount} Tools</Tag>
            </Tooltip>
            <Tooltip title="Resources">
              <Tag color="green">{resourceCount} Resources</Tag>
            </Tooltip>
            <Tooltip title="Prompts">
              <Tag color="purple">{promptCount} Prompts</Tag>
            </Tooltip>
          </Space>
        </div>

        {/* Last Health Check */}
        <div className="flex items-center gap-1 text-xs text-gray-500">
          <ClockCircleOutlined />
          <span>Last check: {formatDate(server.last_health_check)}</span>
        </div>

        {/* Error Message */}
        {server.last_error && (
          <div className="bg-red-50 border border-red-200 rounded p-2">
            <Text type="danger" className="text-xs">
              {server.last_error}
            </Text>
          </div>
        )}
      </div>
    </Card>
  );
};
