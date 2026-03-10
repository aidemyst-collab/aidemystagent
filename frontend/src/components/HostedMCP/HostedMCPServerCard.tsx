import { Card, Tag, Typography, Space, Button, Tooltip, Popconfirm, Badge } from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  ReloadOutlined,
  DeleteOutlined,
  FileTextOutlined,
  SearchOutlined,
  CopyOutlined,
  ToolOutlined,
  FolderOutlined,
  MessageOutlined,
  CloudOutlined,
} from '@ant-design/icons';
import {
  type HostedMCPServer,
  statusColors,
  statusDisplayNames,
  sourceTypeDisplayNames,
} from '../../features/hosted-mcp/hostedMcpServerService';

const { Text, Paragraph } = Typography;

interface HostedMCPServerCardProps {
  server: HostedMCPServer;
  onStart: (serverId: string) => void;
  onStop: (serverId: string) => void;
  onRedeploy: (serverId: string) => void;
  onViewLogs: (serverId: string) => void;
  onDiscover: (serverId: string) => void;
  onDelete: (serverId: string) => void;
  isStarting?: boolean;
  isStopping?: boolean;
  isRedeploying?: boolean;
  isDiscovering?: boolean;
}

export const HostedMCPServerCard = ({
  server,
  onStart,
  onStop,
  onRedeploy,
  onViewLogs,
  onDiscover,
  onDelete,
  isStarting,
  isStopping,
  isRedeploying,
  isDiscovering,
}: HostedMCPServerCardProps) => {
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const isRunning = server.status === 'running';
  const isStopped = server.status === 'stopped';
  const isDeploying = server.status === 'deploying' || server.status === 'pending';
  const isFailed = server.status === 'failed';

  // Get source display info
  const getSourceDisplay = () => {
    const config = server.source_config;
    if (server.source_type === 'docker' && 'image' in config) {
      return config.image;
    } else if (server.source_type === 'registry' && 'package' in config) {
      return `${config.package}@${config.version || 'latest'}`;
    } else if (server.source_type === 'github' && 'repo' in config) {
      return `${config.repo}:${config.branch || 'main'}`;
    }
    return 'Unknown';
  };

  return (
    <Card
      hoverable
      className="h-full"
      actions={[
        <Tooltip title="View Logs" key="logs">
          <Button
            type="text"
            icon={<FileTextOutlined />}
            onClick={() => onViewLogs(server.id)}
          />
        </Tooltip>,
        isRunning ? (
          <Tooltip title="Stop Server" key="stop">
            <Button
              type="text"
              icon={<PauseCircleOutlined />}
              onClick={() => onStop(server.id)}
              loading={isStopping}
            />
          </Tooltip>
        ) : (
          <Tooltip title="Start Server" key="start">
            <Button
              type="text"
              icon={<PlayCircleOutlined />}
              onClick={() => onStart(server.id)}
              loading={isStarting}
              disabled={isDeploying}
            />
          </Tooltip>
        ),
        <Tooltip title="Discover Capabilities" key="discover">
          <Button
            type="text"
            icon={<SearchOutlined />}
            onClick={() => onDiscover(server.id)}
            loading={isDiscovering}
            disabled={!isRunning}
          />
        </Tooltip>,
        <Tooltip title="Redeploy" key="redeploy">
          <Button
            type="text"
            icon={<ReloadOutlined />}
            onClick={() => onRedeploy(server.id)}
            loading={isRedeploying}
            disabled={isDeploying}
          />
        </Tooltip>,
        <Popconfirm
          title="Delete this server?"
          description="This will stop and remove the server from Azure."
          onConfirm={() => onDelete(server.id)}
          okText="Delete"
          okType="danger"
          cancelText="Cancel"
          key="delete"
        >
          <Tooltip title="Delete">
            <Button type="text" danger icon={<DeleteOutlined />} />
          </Tooltip>
        </Popconfirm>,
      ]}
    >
      {/* Header */}
      <div className="flex justify-between items-start mb-3">
        <div className="flex-1 mr-2">
          <Text strong className="text-lg block truncate" title={server.name}>
            {server.name}
          </Text>
          {server.description && (
            <Paragraph
              type="secondary"
              className="text-sm mb-0 mt-1"
              ellipsis={{ rows: 2 }}
            >
              {server.description}
            </Paragraph>
          )}
        </div>
        <Tag color={statusColors[server.status] as any}>
          {statusDisplayNames[server.status]}
        </Tag>
      </div>

      {/* Source Type */}
      <div className="mb-3">
        <Space size="small">
          <Tag icon={<CloudOutlined />} color="geekblue">
            {sourceTypeDisplayNames[server.source_type]}
          </Tag>
        </Space>
      </div>

      {/* Source Details */}
      <div className="mb-3">
        <Text type="secondary" className="text-xs block mb-1">Source</Text>
        <div className="flex items-center gap-2">
          <Text code className="text-xs truncate flex-1" title={getSourceDisplay()}>
            {getSourceDisplay()}
          </Text>
          <Tooltip title="Copy">
            <Button
              type="text"
              size="small"
              icon={<CopyOutlined />}
              onClick={() => copyToClipboard(getSourceDisplay())}
            />
          </Tooltip>
        </div>
      </div>

      {/* Azure URL */}
      {server.azure_app_url && (
        <div className="mb-3">
          <Text type="secondary" className="text-xs block mb-1">Internal URL</Text>
          <div className="flex items-center gap-2">
            <Text code className="text-xs truncate flex-1" title={server.azure_app_url}>
              {server.azure_app_url}
            </Text>
            <Tooltip title="Copy URL">
              <Button
                type="text"
                size="small"
                icon={<CopyOutlined />}
                onClick={() => copyToClipboard(server.azure_app_url || '')}
              />
            </Tooltip>
          </div>
        </div>
      )}

      {/* Resources */}
      <div className="mb-3">
        <Text type="secondary" className="text-xs block mb-1">Resources</Text>
        <div className="flex items-center gap-1 text-xs">
          <Tag className="m-0">{server.cpu_cores} vCPU</Tag>
          <Tag className="m-0">{server.memory_gb} GB</Tag>
          <Tag className="m-0">{server.min_replicas}-{server.max_replicas} replicas</Tag>
        </div>
      </div>

      {/* Discovered Capabilities */}
      <div className="mb-2">
        <Text type="secondary" className="text-xs block mb-1">Capabilities</Text>
        <Space size={4}>
          <Badge count={server.tool_count} showZero color={server.tool_count > 0 ? 'blue' : 'default'}>
            <Tag icon={<ToolOutlined />} className="m-0">Tools</Tag>
          </Badge>
          <Badge count={server.resource_count} showZero color={server.resource_count > 0 ? 'green' : 'default'}>
            <Tag icon={<FolderOutlined />} className="m-0">Resources</Tag>
          </Badge>
          <Badge count={server.prompt_count} showZero color={server.prompt_count > 0 ? 'purple' : 'default'}>
            <Tag icon={<MessageOutlined />} className="m-0">Prompts</Tag>
          </Badge>
        </Space>
      </div>

      {/* Error Message */}
      {isFailed && server.error_message && (
        <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded">
          <Text type="danger" className="text-xs">
            {server.error_message}
          </Text>
        </div>
      )}

      {/* Last Health Check */}
      {server.last_health_check && (
        <div className="mt-2">
          <Text type="secondary" className="text-xs">
            Last check: {new Date(server.last_health_check).toLocaleString()}
          </Text>
        </div>
      )}
    </Card>
  );
};

export default HostedMCPServerCard;
