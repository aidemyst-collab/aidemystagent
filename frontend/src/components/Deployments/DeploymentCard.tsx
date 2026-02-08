import React from 'react';
import { Card, Tag, Button, Space, Tooltip } from 'antd';
import {
  PlayCircleOutlined,
  StopOutlined,
  ReloadOutlined,
  DeleteOutlined,
  CopyOutlined,
  ExportOutlined,
} from '@ant-design/icons';

interface DeploymentCardProps {
  id: string;
  agentName: string;
  version: string;
  environment: string;
  status: string;
  endpointUrl?: string;
  apiKey?: string;
  deployedAt?: string;
  onStop: (id: string) => void;
  onRestart: (id: string) => void;
  onDelete: (id: string) => void;
  onExport: (id: string) => void;
}

const statusColors: Record<string, string> = {
  pending: 'orange',
  deploying: 'blue',
  active: 'green',
  failed: 'red',
  stopped: 'default',
};

const environmentColors: Record<string, string> = {
  development: 'blue',
  staging: 'orange',
  production: 'red',
};

export const DeploymentCard: React.FC<DeploymentCardProps> = ({
  id,
  agentName,
  version,
  environment,
  status,
  endpointUrl,
  apiKey,
  deployedAt,
  onStop,
  onRestart,
  onDelete,
  onExport,
}) => {
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <Card
      title={
        <div className="flex justify-between items-center">
          <span className="font-semibold">{agentName}</span>
          <Space>
            <Tag color={environmentColors[environment]}>
              {environment.toUpperCase()}
            </Tag>
            <Tag color={statusColors[status]}>{status.toUpperCase()}</Tag>
          </Space>
        </div>
      }
      extra={
        <Space>
          <Tooltip title="Export JSON">
            <Button
              type="text"
              size="small"
              icon={<ExportOutlined />}
              onClick={() => onExport(id)}
            />
          </Tooltip>
          {status === 'active' && (
            <Tooltip title="Stop Deployment">
              <Button
                type="text"
                size="small"
                icon={<StopOutlined />}
                onClick={() => onStop(id)}
              />
            </Tooltip>
          )}
          {(status === 'stopped' || status === 'failed') && (
            <Tooltip title="Restart Deployment">
              <Button
                type="text"
                size="small"
                icon={<ReloadOutlined />}
                onClick={() => onRestart(id)}
              />
            </Tooltip>
          )}
          <Tooltip title="Delete Deployment">
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={() => onDelete(id)}
            />
          </Tooltip>
        </Space>
      }
    >
      <Space direction="vertical" className="w-full">
        <div>
          <span className="text-gray-500">Version:</span>{' '}
          <span className="font-mono">{version}</span>
        </div>

        {deployedAt && (
          <div>
            <span className="text-gray-500">Deployed:</span>{' '}
            {new Date(deployedAt).toLocaleString()}
          </div>
        )}

        {endpointUrl && (
          <div className="flex justify-between items-center bg-gray-50 p-2 rounded">
            <span className="text-xs font-mono truncate">{endpointUrl}</span>
            <Tooltip title="Copy Endpoint">
              <Button
                type="text"
                size="small"
                icon={<CopyOutlined />}
                onClick={() => copyToClipboard(endpointUrl)}
              />
            </Tooltip>
          </div>
        )}

        {apiKey && status === 'active' && (
          <div className="flex justify-between items-center bg-gray-50 p-2 rounded">
            <span className="text-xs font-mono">API Key: {apiKey.slice(0, 20)}...</span>
            <Tooltip title="Copy API Key">
              <Button
                type="text"
                size="small"
                icon={<CopyOutlined />}
                onClick={() => copyToClipboard(apiKey)}
              />
            </Tooltip>
          </div>
        )}
      </Space>
    </Card>
  );
};
