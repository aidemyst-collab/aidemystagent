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
  Checkbox,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  CloudServerOutlined,
  ImportOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { MCPServerCard } from '../components/MCPServers/MCPServerCard';
import { MCPServerModal } from '../components/MCPServers/MCPServerModal';
import {
  mcpServerService,
  type MCPServer,
  type MCPServerDiscoveryResponse,
} from '../features/mcp-servers/mcpServerService';

const { Title, Text } = Typography;

export const MCPServers = () => {
  const [modalVisible, setModalVisible] = useState(false);
  const [editingServer, setEditingServer] = useState<MCPServer | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [discoveryModalVisible, setDiscoveryModalVisible] = useState(false);
  const [discoveryResult, setDiscoveryResult] = useState<MCPServerDiscoveryResponse | null>(null);
  const [discoveryServerId, setDiscoveryServerId] = useState<string | null>(null);
  const [testingServerId, setTestingServerId] = useState<string | null>(null);
  const [selectedTools, setSelectedTools] = useState<string[]>([]);

  const queryClient = useQueryClient();

  // Fetch servers
  const {
    data,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['mcp-servers', statusFilter],
    queryFn: () => mcpServerService.getServers(0, 100, statusFilter),
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (serverId: string) => mcpServerService.deleteServer(serverId),
    onSuccess: () => {
      message.success('MCP server deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['mcp-servers'] });
    },
    onError: (error: any) => {
      message.error(error.message || 'Failed to delete MCP server');
    },
  });

  // Test connection mutation
  const testMutation = useMutation({
    mutationFn: (serverId: string) => mcpServerService.testConnection(serverId),
    onSuccess: (result) => {
      if (result.success) {
        message.success(`Connection successful (${result.response_time_ms}ms)`);
      } else {
        message.error(result.error || 'Connection failed');
      }
      queryClient.invalidateQueries({ queryKey: ['mcp-servers'] });
      setTestingServerId(null);
    },
    onError: (error: any) => {
      message.error(error.message || 'Failed to test connection');
      setTestingServerId(null);
    },
  });

  // Discover capabilities mutation
  const discoverMutation = useMutation({
    mutationFn: (serverId: string) => mcpServerService.discoverCapabilities(serverId),
    onSuccess: (result, serverId) => {
      setDiscoveryResult(result);
      setDiscoveryServerId(serverId);
      setDiscoveryModalVisible(true);
      setSelectedTools([]); // Reset selection
      queryClient.invalidateQueries({ queryKey: ['mcp-servers'] });
    },
    onError: (error: any) => {
      message.error(error.message || 'Failed to discover capabilities');
    },
  });

  // Import tools mutation
  const importMutation = useMutation({
    mutationFn: ({ serverId, toolNames }: { serverId: string; toolNames: string[] }) =>
      mcpServerService.importTools(serverId, toolNames),
    onSuccess: (result) => {
      if (result.success) {
        message.success(
          `Imported ${result.imported_count} tool(s). ${result.skipped_count > 0 ? `Skipped ${result.skipped_count}.` : ''}`
        );
        if (result.skipped_tools.length > 0) {
          console.log('Skipped tools:', result.skipped_tools);
        }
      } else {
        message.error(result.error || 'Failed to import tools');
      }
      setSelectedTools([]);
      queryClient.invalidateQueries({ queryKey: ['tools'] }); // Refresh tools list
    },
    onError: (error: any) => {
      message.error(error.message || 'Failed to import tools');
    },
  });

  const handleCreateServer = () => {
    setEditingServer(null);
    setModalVisible(true);
  };

  const handleEditServer = (server: MCPServer) => {
    setEditingServer(server);
    setModalVisible(true);
  };

  const handleDeleteServer = (serverId: string) => {
    deleteMutation.mutate(serverId);
  };

  const handleTestConnection = (serverId: string) => {
    setTestingServerId(serverId);
    testMutation.mutate(serverId);
  };

  const handleDiscoverCapabilities = (serverId: string) => {
    discoverMutation.mutate(serverId);
  };

  const handleImportTools = () => {
    if (!discoveryServerId || selectedTools.length === 0) return;
    importMutation.mutate({ serverId: discoveryServerId, toolNames: selectedTools });
  };

  const handleToolSelect = (toolName: string, checked: boolean) => {
    if (checked) {
      setSelectedTools([...selectedTools, toolName]);
    } else {
      setSelectedTools(selectedTools.filter((t) => t !== toolName));
    }
  };

  const handleSelectAllTools = (checked: boolean) => {
    if (checked && discoveryResult?.tools) {
      setSelectedTools(discoveryResult.tools.map((t) => t.name));
    } else {
      setSelectedTools([]);
    }
  };

  const servers = data?.servers || [];

  return (
    <div>
      {/* Header */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <Title level={2} className="mb-2 flex items-center gap-2">
            <CloudServerOutlined />
            MCP Servers
          </Title>
          <Text type="secondary">
            Manage your MCP server connections. Register servers to easily discover and use their tools.
          </Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
            Refresh
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateServer}>
            Add Server
          </Button>
        </Space>
      </div>

      {/* Filters */}
      <div className="mb-4">
        <Space>
          <Text>Filter by status:</Text>
          <Select
            value={statusFilter}
            onChange={setStatusFilter}
            style={{ width: 150 }}
            allowClear
            placeholder="All statuses"
          >
            <Select.Option value="active">Active</Select.Option>
            <Select.Option value="inactive">Inactive</Select.Option>
            <Select.Option value="error">Error</Select.Option>
          </Select>
        </Space>
      </div>

      {/* Server List */}
      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <Spin size="large" />
        </div>
      ) : servers.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <div className="text-center">
              <Text type="secondary">No MCP servers registered yet</Text>
              <br />
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleCreateServer}
                className="mt-4"
              >
                Add Your First Server
              </Button>
            </div>
          }
        />
      ) : (
        <Row gutter={[16, 16]}>
          {servers.map((server) => (
            <Col key={server.id} xs={24} sm={24} md={12} lg={8} xl={6}>
              <MCPServerCard
                server={server}
                onTest={() => handleTestConnection(server.id)}
                onDiscover={() => handleDiscoverCapabilities(server.id)}
                onEdit={() => handleEditServer(server)}
                onDelete={() => handleDeleteServer(server.id)}
                loading={
                  testingServerId === server.id ||
                  discoverMutation.isPending
                }
              />
            </Col>
          ))}
        </Row>
      )}

      {/* Create/Edit Modal */}
      <MCPServerModal
        visible={modalVisible}
        onClose={() => {
          setModalVisible(false);
          setEditingServer(null);
        }}
        editingServer={editingServer}
      />

      {/* Discovery Results Modal */}
      <Modal
        title="Discovered Capabilities"
        open={discoveryModalVisible}
        onCancel={() => {
          setDiscoveryModalVisible(false);
          setDiscoveryResult(null);
          setDiscoveryServerId(null);
          setSelectedTools([]);
        }}
        footer={
          discoveryResult?.success && discoveryResult.tools.length > 0 ? (
            <div className="flex justify-between items-center">
              <Text type="secondary">
                {selectedTools.length} tool(s) selected
              </Text>
              <Space>
                <Button
                  onClick={() => {
                    setDiscoveryModalVisible(false);
                    setDiscoveryResult(null);
                    setDiscoveryServerId(null);
                    setSelectedTools([]);
                  }}
                >
                  Cancel
                </Button>
                <Button
                  type="primary"
                  icon={<ImportOutlined />}
                  onClick={handleImportTools}
                  loading={importMutation.isPending}
                  disabled={selectedTools.length === 0}
                >
                  Import Selected Tools
                </Button>
              </Space>
            </div>
          ) : null
        }
        width={700}
      >
        {discoveryResult && (
          <div className="space-y-4">
            {discoveryResult.success ? (
              <>
                {/* Info Alert */}
                <Alert
                  message="Import Tools to Use in Workflows"
                  description="Select the tools you want to import. Imported tools will appear in your Tools library and can be used in workflow nodes."
                  type="info"
                  showIcon
                  className="mb-4"
                />

                {/* Tools */}
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <Title level={5} className="mb-0">
                      Tools ({discoveryResult.tools.length})
                    </Title>
                    {discoveryResult.tools.length > 0 && (
                      <Checkbox
                        checked={selectedTools.length === discoveryResult.tools.length}
                        indeterminate={selectedTools.length > 0 && selectedTools.length < discoveryResult.tools.length}
                        onChange={(e) => handleSelectAllTools(e.target.checked)}
                      >
                        Select All
                      </Checkbox>
                    )}
                  </div>
                  {discoveryResult.tools.length > 0 ? (
                    <List
                      size="small"
                      bordered
                      dataSource={discoveryResult.tools}
                      renderItem={(tool) => (
                        <List.Item>
                          <Checkbox
                            checked={selectedTools.includes(tool.name)}
                            onChange={(e) => handleToolSelect(tool.name, e.target.checked)}
                            style={{ marginRight: 12 }}
                          />
                          <List.Item.Meta
                            title={
                              <Space>
                                <Tag color="blue">{tool.name}</Tag>
                              </Space>
                            }
                            description={tool.description || 'No description'}
                          />
                        </List.Item>
                      )}
                    />
                  ) : (
                    <Text type="secondary">No tools discovered</Text>
                  )}
                </div>

                {/* Resources */}
                <div>
                  <Title level={5}>
                    Resources ({discoveryResult.resources.length})
                  </Title>
                  {discoveryResult.resources.length > 0 ? (
                    <List
                      size="small"
                      bordered
                      dataSource={discoveryResult.resources}
                      renderItem={(resource) => (
                        <List.Item>
                          <List.Item.Meta
                            title={
                              <Space>
                                <Tag color="green">{resource.name || resource.uri}</Tag>
                                {resource.mime_type && (
                                  <Tag>{resource.mime_type}</Tag>
                                )}
                              </Space>
                            }
                            description={resource.description || resource.uri}
                          />
                        </List.Item>
                      )}
                    />
                  ) : (
                    <Text type="secondary">No resources discovered</Text>
                  )}
                </div>

                {/* Prompts */}
                <div>
                  <Title level={5}>
                    Prompts ({discoveryResult.prompts.length})
                  </Title>
                  {discoveryResult.prompts.length > 0 ? (
                    <List
                      size="small"
                      bordered
                      dataSource={discoveryResult.prompts}
                      renderItem={(prompt) => (
                        <List.Item>
                          <List.Item.Meta
                            title={
                              <Tag color="purple">{prompt.name}</Tag>
                            }
                            description={prompt.description || 'No description'}
                          />
                        </List.Item>
                      )}
                    />
                  ) : (
                    <Text type="secondary">No prompts discovered</Text>
                  )}
                </div>
              </>
            ) : (
              <div className="text-center py-4">
                <Text type="danger">
                  Discovery failed: {discoveryResult.error}
                </Text>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};
