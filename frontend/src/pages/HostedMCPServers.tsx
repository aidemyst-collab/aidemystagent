import { useState } from 'react';
import {
  Typography,
  Row,
  Col,
  Button,
  Spin,
  Empty,
  message,
  Select,
  Space,
  Modal,
  Tag,
  List,
  Tabs,
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  CloudServerOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { HostedMCPServerCard } from '../components/HostedMCP/HostedMCPServerCard';
import { DeploymentWizard } from '../components/HostedMCP/DeploymentWizard';
import { LogsViewer } from '../components/HostedMCP/LogsViewer';
import {
  hostedMcpServerService,
  type HostedMCPServer,
  type HostedMCPServerStatus,
  type HostedMCPServerDiscoveryResponse,
  statusDisplayNames,
} from '../features/hosted-mcp/hostedMcpServerService';

const { Title, Text } = Typography;

export const HostedMCPServers = () => {
  const [modalVisible, setModalVisible] = useState(false);
  const [statusFilter, setStatusFilter] = useState<HostedMCPServerStatus | undefined>(undefined);
  const [logsModalVisible, setLogsModalVisible] = useState(false);
  const [logsServerId, setLogsServerId] = useState<string | null>(null);
  const [discoveryModalVisible, setDiscoveryModalVisible] = useState(false);
  const [discoveryResult, setDiscoveryResult] = useState<HostedMCPServerDiscoveryResponse | null>(null);

  const queryClient = useQueryClient();

  // Fetch servers
  const {
    data,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['hosted-mcp-servers', statusFilter],
    queryFn: () => hostedMcpServerService.getServers(0, 100, statusFilter),
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (serverId: string) => hostedMcpServerService.deleteServer(serverId),
    onSuccess: () => {
      message.success('Hosted MCP server deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['hosted-mcp-servers'] });
    },
    onError: (error: any) => {
      message.error(error.message || 'Failed to delete server');
    },
  });

  // Start mutation
  const startMutation = useMutation({
    mutationFn: (serverId: string) => hostedMcpServerService.startServer(serverId),
    onSuccess: () => {
      message.success('Server starting...');
      queryClient.invalidateQueries({ queryKey: ['hosted-mcp-servers'] });
    },
    onError: (error: any) => {
      message.error(error.message || 'Failed to start server');
    },
  });

  // Stop mutation
  const stopMutation = useMutation({
    mutationFn: (serverId: string) => hostedMcpServerService.stopServer(serverId),
    onSuccess: () => {
      message.success('Server stopping...');
      queryClient.invalidateQueries({ queryKey: ['hosted-mcp-servers'] });
    },
    onError: (error: any) => {
      message.error(error.message || 'Failed to stop server');
    },
  });

  // Redeploy mutation
  const redeployMutation = useMutation({
    mutationFn: (serverId: string) => hostedMcpServerService.redeployServer(serverId),
    onSuccess: () => {
      message.success('Server redeploying...');
      queryClient.invalidateQueries({ queryKey: ['hosted-mcp-servers'] });
    },
    onError: (error: any) => {
      message.error(error.message || 'Failed to redeploy server');
    },
  });

  // Discover capabilities mutation
  const discoverMutation = useMutation({
    mutationFn: (serverId: string) => hostedMcpServerService.discoverCapabilities(serverId),
    onSuccess: (result) => {
      setDiscoveryResult(result);
      setDiscoveryModalVisible(true);
      queryClient.invalidateQueries({ queryKey: ['hosted-mcp-servers'] });
    },
    onError: (error: any) => {
      message.error(error.message || 'Failed to discover capabilities');
    },
  });

  const handleDeployServer = () => {
    setModalVisible(true);
  };

  const handleDeleteServer = (serverId: string) => {
    Modal.confirm({
      title: 'Delete Hosted MCP Server',
      content: 'This will stop and remove the server from Azure. Are you sure?',
      okText: 'Delete',
      okType: 'danger',
      cancelText: 'Cancel',
      onOk: () => deleteMutation.mutate(serverId),
    });
  };

  const handleStartServer = (serverId: string) => {
    startMutation.mutate(serverId);
  };

  const handleStopServer = (serverId: string) => {
    stopMutation.mutate(serverId);
  };

  const handleRedeployServer = (serverId: string) => {
    redeployMutation.mutate(serverId);
  };

  const handleViewLogs = (serverId: string) => {
    setLogsServerId(serverId);
    setLogsModalVisible(true);
  };

  const handleDiscoverCapabilities = (serverId: string) => {
    discoverMutation.mutate(serverId);
  };

  const handleModalClose = () => {
    setModalVisible(false);
    queryClient.invalidateQueries({ queryKey: ['hosted-mcp-servers'] });
  };

  const servers = data?.servers || [];

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <Title level={2} className="mb-1">
            <CloudServerOutlined className="mr-2" />
            Hosted MCP Servers
          </Title>
          <Text type="secondary">
            Deploy and manage MCP servers on Azure Container Apps
          </Text>
        </div>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => refetch()}
            loading={isLoading}
          >
            Refresh
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleDeployServer}
          >
            Deploy Server
          </Button>
        </Space>
      </div>

      {/* Filters */}
      <div className="mb-6">
        <Space>
          <Text>Status:</Text>
          <Select
            placeholder="All statuses"
            allowClear
            value={statusFilter}
            onChange={(value) => setStatusFilter(value)}
            style={{ width: 150 }}
            options={[
              { value: 'pending', label: statusDisplayNames.pending },
              { value: 'deploying', label: statusDisplayNames.deploying },
              { value: 'running', label: statusDisplayNames.running },
              { value: 'stopped', label: statusDisplayNames.stopped },
              { value: 'failed', label: statusDisplayNames.failed },
            ]}
          />
        </Space>
      </div>

      {/* Server Grid */}
      {isLoading ? (
        <div className="flex justify-center items-center py-12">
          <Spin size="large" />
        </div>
      ) : servers.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <span>
              No hosted MCP servers yet.{' '}
              <Button type="link" onClick={handleDeployServer}>
                Deploy your first server
              </Button>
            </span>
          }
        />
      ) : (
        <Row gutter={[16, 16]}>
          {servers.map((server) => (
            <Col xs={24} sm={12} lg={8} key={server.id}>
              <HostedMCPServerCard
                server={server}
                onStart={handleStartServer}
                onStop={handleStopServer}
                onRedeploy={handleRedeployServer}
                onViewLogs={handleViewLogs}
                onDiscover={handleDiscoverCapabilities}
                onDelete={handleDeleteServer}
                isStarting={startMutation.isPending}
                isStopping={stopMutation.isPending}
                isRedeploying={redeployMutation.isPending}
                isDiscovering={discoverMutation.isPending}
              />
            </Col>
          ))}
        </Row>
      )}

      {/* Deployment Wizard Modal */}
      <DeploymentWizard
        visible={modalVisible}
        onClose={handleModalClose}
      />

      {/* Logs Viewer Modal */}
      <LogsViewer
        visible={logsModalVisible}
        serverId={logsServerId}
        onClose={() => {
          setLogsModalVisible(false);
          setLogsServerId(null);
        }}
      />

      {/* Discovery Results Modal */}
      <Modal
        title="Discovered Capabilities"
        open={discoveryModalVisible}
        onCancel={() => setDiscoveryModalVisible(false)}
        footer={null}
        width={700}
      >
        {discoveryResult && (
          <Tabs
            items={[
              {
                key: 'tools',
                label: `Tools (${discoveryResult.tools.length})`,
                children: (
                  <List
                    dataSource={discoveryResult.tools}
                    renderItem={(tool) => (
                      <List.Item>
                        <List.Item.Meta
                          title={<Tag color="blue">{tool.name}</Tag>}
                          description={tool.description || 'No description'}
                        />
                      </List.Item>
                    )}
                    locale={{ emptyText: 'No tools discovered' }}
                  />
                ),
              },
              {
                key: 'resources',
                label: `Resources (${discoveryResult.resources.length})`,
                children: (
                  <List
                    dataSource={discoveryResult.resources}
                    renderItem={(resource) => (
                      <List.Item>
                        <List.Item.Meta
                          title={<Tag color="green">{resource.uri}</Tag>}
                          description={resource.description || resource.name || 'No description'}
                        />
                      </List.Item>
                    )}
                    locale={{ emptyText: 'No resources discovered' }}
                  />
                ),
              },
              {
                key: 'prompts',
                label: `Prompts (${discoveryResult.prompts.length})`,
                children: (
                  <List
                    dataSource={discoveryResult.prompts}
                    renderItem={(prompt) => (
                      <List.Item>
                        <List.Item.Meta
                          title={<Tag color="purple">{prompt.name}</Tag>}
                          description={prompt.description || 'No description'}
                        />
                      </List.Item>
                    )}
                    locale={{ emptyText: 'No prompts discovered' }}
                  />
                ),
              },
            ]}
          />
        )}
      </Modal>
    </div>
  );
};

export default HostedMCPServers;
