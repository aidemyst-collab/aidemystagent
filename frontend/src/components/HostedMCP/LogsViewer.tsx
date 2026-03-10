import { useEffect, useState } from 'react';
import { Modal, Button, Spin, Typography, Space, Empty, message } from 'antd';
import { ReloadOutlined, CopyOutlined, DownloadOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { hostedMcpServerService } from '../../features/hosted-mcp/hostedMcpServerService';

const { Text } = Typography;

interface LogsViewerProps {
  visible: boolean;
  serverId: string | null;
  onClose: () => void;
}

export const LogsViewer = ({ visible, serverId, onClose }: LogsViewerProps) => {
  const [lines, setLines] = useState(100);

  const {
    data,
    isLoading,
    refetch,
    error,
  } = useQuery({
    queryKey: ['hosted-mcp-server-logs', serverId, lines],
    queryFn: () => serverId ? hostedMcpServerService.getLogs(serverId, lines) : null,
    enabled: visible && !!serverId,
    refetchInterval: visible ? 10000 : false, // Refresh every 10 seconds when visible
  });

  useEffect(() => {
    if (visible && serverId) {
      refetch();
    }
  }, [visible, serverId, refetch]);

  const handleCopyLogs = () => {
    if (data?.logs) {
      navigator.clipboard.writeText(data.logs);
      message.success('Logs copied to clipboard');
    }
  };

  const handleDownloadLogs = () => {
    if (data?.logs) {
      const blob = new Blob([data.logs], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `mcp-server-${serverId}-logs.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  return (
    <Modal
      title="Container Logs"
      open={visible}
      onCancel={onClose}
      width={900}
      footer={[
        <Button key="close" onClick={onClose}>
          Close
        </Button>,
      ]}
      destroyOnClose
    >
      {/* Toolbar */}
      <div className="flex justify-between items-center mb-4">
        <Space>
          <Text type="secondary">Lines:</Text>
          <select
            value={lines}
            onChange={(e) => setLines(Number(e.target.value))}
            className="border rounded px-2 py-1"
          >
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={200}>200</option>
            <option value={500}>500</option>
          </select>
        </Space>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => refetch()}
            loading={isLoading}
          >
            Refresh
          </Button>
          <Button
            icon={<CopyOutlined />}
            onClick={handleCopyLogs}
            disabled={!data?.logs}
          >
            Copy
          </Button>
          <Button
            icon={<DownloadOutlined />}
            onClick={handleDownloadLogs}
            disabled={!data?.logs}
          >
            Download
          </Button>
        </Space>
      </div>

      {/* Logs Display */}
      <div
        className="bg-gray-900 rounded-lg p-4 font-mono text-sm text-green-400 overflow-auto"
        style={{ maxHeight: '500px', minHeight: '300px' }}
      >
        {isLoading ? (
          <div className="flex justify-center items-center h-64">
            <Spin tip="Loading logs..." />
          </div>
        ) : error ? (
          <div className="text-red-400">
            Error loading logs: {(error as Error).message}
          </div>
        ) : data?.logs ? (
          <pre className="whitespace-pre-wrap m-0">{data.logs}</pre>
        ) : (
          <Empty
            description={<span className="text-gray-400">No logs available</span>}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        )}
      </div>

      {/* Timestamp */}
      {data?.timestamp && (
        <div className="mt-2 text-right">
          <Text type="secondary" className="text-xs">
            Last fetched: {new Date(data.timestamp).toLocaleString()}
          </Text>
        </div>
      )}
    </Modal>
  );
};

export default LogsViewer;
