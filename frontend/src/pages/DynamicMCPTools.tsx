// Tool Providers page - updated 2026-03-08
import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Space,
  Table,
  Tag,
  Tooltip,
  message,
  Modal,
  Switch,
  Typography,
  Empty,
  Collapse,
  Badge,
  Dropdown,
  Input,
  Spin,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  ApiOutlined,
  MoreOutlined,
  ReloadOutlined,
  CloudServerOutlined,
  ToolOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SearchOutlined,
  CodeOutlined,
} from '@ant-design/icons';
import { MainLayout } from '../components/Common/MainLayout';
import { DynamicMCPServerModal } from '../components/MCPTools/DynamicMCPServerModal';
import {
  DynamicMCPServer,
  DynamicMCPTool,
  dynamicMcpServerService,
} from '../features/mcp-tools/dynamicMcpServerService';
import { apiClient } from '../services/api';

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;
const { confirm } = Modal;

interface CredentialOption {
  id: string;
  name: string;
}

export const DynamicMCPTools: React.FC = () => {
  const [servers, setServers] = useState<DynamicMCPServer[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingServer, setEditingServer] = useState<DynamicMCPServer | undefined>();
  const [credentials, setCredentials] = useState<CredentialOption[]>([]);
  const [expandedServers, setExpandedServers] = useState<string[]>([]);
  const [testingTool, setTestingTool] = useState<{
    serverId: string;
    toolId: string;
    loading: boolean;
  } | null>(null);

  // Load servers and credentials
  useEffect(() => {
    loadServers();
    loadCredentials();
  }, []);

  const loadServers = async () => {
    try {
      setLoading(true);
      const response = await dynamicMcpServerService.getServers();
      setServers(response.servers);
    } catch (error: any) {
      console.error('Failed to load servers:', error);
      message.error('Failed to load servers');
    } finally {
      setLoading(false);
    }
  };

  const loadCredentials = async () => {
    try {
      const response = await apiClient.get<{ credentials: any[] }>('/credentials');
      setCredentials(
        response.credentials?.map((c: any) => ({ id: c.id, name: c.name })) || []
      );
    } catch (error) {
      console.error('Failed to load credentials:', error);
    }
  };

  // Filter servers by search text
  const filteredServers = servers.filter((server) => {
    const search = searchText.toLowerCase();
    const matchesServer =
      server.name.toLowerCase().includes(search) ||
      server.base_url.toLowerCase().includes(search) ||
      (server.description?.toLowerCase().includes(search) ?? false);
    const matchesTools = server.tools?.some(
      (tool) =>
        tool.name.toLowerCase().includes(search) ||
        tool.path.toLowerCase().includes(search)
    );
    return matchesServer || matchesTools;
  });

  // Server actions
  const handleCreateServer = () => {
    setEditingServer(undefined);
    setModalOpen(true);
  };

  const handleEditServer = (server: DynamicMCPServer) => {
    setEditingServer(server);
    setModalOpen(true);
  };

  const handleDeleteServer = (server: DynamicMCPServer) => {
    confirm({
      title: 'Delete Provider',
      content: (
        <div>
          <p>Are you sure you want to delete "{server.name}"?</p>
          <p>
            <Text type="danger">
              This will also delete all {server.tool_count} tools in this provider.
            </Text>
          </p>
        </div>
      ),
      okText: 'Delete',
      okType: 'danger',
      onOk: async () => {
        try {
          await dynamicMcpServerService.deleteServer(server.id);
          message.success('Provider deleted');
          loadServers();
        } catch (error: any) {
          message.error(error?.message || 'Failed to delete provider');
        }
      },
    });
  };

  const handleToggleServer = async (server: DynamicMCPServer) => {
    try {
      await dynamicMcpServerService.toggleServer(server.id);
      message.success(`Provider ${server.is_active ? 'disabled' : 'enabled'}`);
      loadServers();
    } catch (error: any) {
      message.error(error?.message || 'Failed to toggle provider');
    }
  };

  // Tool actions
  const handleToggleTool = async (serverId: string, tool: DynamicMCPTool) => {
    try {
      await dynamicMcpServerService.toggleTool(serverId, tool.id);
      message.success(`Tool ${tool.is_active ? 'disabled' : 'enabled'}`);
      loadServers();
    } catch (error: any) {
      message.error(error?.message || 'Failed to toggle tool');
    }
  };

  const handleDeleteTool = (server: DynamicMCPServer, tool: DynamicMCPTool) => {
    confirm({
      title: 'Delete Tool',
      content: `Are you sure you want to delete "${tool.name}"?`,
      okText: 'Delete',
      okType: 'danger',
      onOk: async () => {
        try {
          await dynamicMcpServerService.deleteTool(server.id, tool.id);
          message.success('Tool deleted');
          loadServers();
        } catch (error: any) {
          message.error(error?.message || 'Failed to delete tool');
        }
      },
    });
  };

  const handleTestTool = async (server: DynamicMCPServer, tool: DynamicMCPTool) => {
    setTestingTool({ serverId: server.id, toolId: tool.id, loading: true });
    try {
      const result = await dynamicMcpServerService.testTool(server.id, tool.id, {
        arguments: {},
      });
      if (result.success) {
        message.success(`Tool executed in ${result.execution_time_ms}ms`);
        Modal.info({
          title: 'Tool Result',
          content: (
            <pre style={{ maxHeight: 400, overflow: 'auto', fontSize: 12 }}>
              {JSON.stringify(result.result, null, 2)}
            </pre>
          ),
          width: 600,
        });
      } else {
        message.error(result.error || 'Tool execution failed');
      }
    } catch (error: any) {
      message.error(error?.message || 'Failed to test tool');
    } finally {
      setTestingTool(null);
    }
  };

  // Render tool table
  const renderToolsTable = (server: DynamicMCPServer) => {
    const columns = [
      {
        title: 'Tool Name',
        dataIndex: 'name',
        key: 'name',
        render: (name: string, tool: DynamicMCPTool) => (
          <Space>
            <ToolOutlined />
            <Text strong>{name}</Text>
            {!tool.is_active && <Tag color="default">Disabled</Tag>}
          </Space>
        ),
      },
      {
        title: 'Method',
        dataIndex: 'method',
        key: 'method',
        width: 80,
        render: (method: string) => (
          <Tag color={method === 'GET' ? 'green' : method === 'POST' ? 'blue' : 'orange'}>
            {method}
          </Tag>
        ),
      },
      {
        title: 'Path',
        dataIndex: 'path',
        key: 'path',
        render: (path: string) => (
          <Text code style={{ fontSize: 12 }}>
            {path}
          </Text>
        ),
      },
      {
        title: 'Parameters',
        key: 'parameters',
        width: 100,
        render: (_: any, tool: DynamicMCPTool) => (
          <Tag>{tool.parameters?.length || 0} params</Tag>
        ),
      },
      {
        title: 'Active',
        key: 'active',
        width: 70,
        render: (_: any, tool: DynamicMCPTool) => (
          <Switch
            size="small"
            checked={tool.is_active}
            onChange={() => handleToggleTool(server.id, tool)}
          />
        ),
      },
      {
        title: 'Actions',
        key: 'actions',
        width: 120,
        render: (_: any, tool: DynamicMCPTool) => (
          <Space size="small">
            <Tooltip title="Test">
              <Button
                type="text"
                size="small"
                icon={<PlayCircleOutlined />}
                loading={
                  testingTool?.serverId === server.id &&
                  testingTool?.toolId === tool.id &&
                  testingTool?.loading
                }
                onClick={() => handleTestTool(server, tool)}
              />
            </Tooltip>
            <Tooltip title="Delete">
              <Button
                type="text"
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={() => handleDeleteTool(server, tool)}
              />
            </Tooltip>
          </Space>
        ),
      },
    ];

    return (
      <Table
        size="small"
        dataSource={server.tools || []}
        columns={columns}
        pagination={false}
        rowKey="id"
        locale={{ emptyText: 'No tools defined' }}
      />
    );
  };

  // Render server card
  const renderServerCard = (server: DynamicMCPServer) => {
    const isExpanded = expandedServers.includes(server.id);

    const menuItems = [
      {
        key: 'edit',
        icon: <EditOutlined />,
        label: 'Edit Provider',
        onClick: () => handleEditServer(server),
      },
      {
        key: 'toggle',
        icon: server.is_active ? <CloseCircleOutlined /> : <CheckCircleOutlined />,
        label: server.is_active ? 'Disable Provider' : 'Enable Provider',
        onClick: () => handleToggleServer(server),
      },
      {
        type: 'divider' as const,
      },
      {
        key: 'delete',
        icon: <DeleteOutlined />,
        label: 'Delete Provider',
        danger: true,
        onClick: () => handleDeleteServer(server),
      },
    ];

    return (
      <Card
        key={server.id}
        style={{ marginBottom: 16 }}
        styles={{
          header: {
            backgroundColor: server.is_active ? '#f6ffed' : '#f5f5f5',
            borderBottom: `2px solid ${server.is_active ? '#52c41a' : '#d9d9d9'}`,
          }
        }}
        title={
          <Space>
            <CloudServerOutlined style={{ fontSize: 20 }} />
            <span>{server.name}</span>
            {server.is_active ? (
              <Badge status="success" text="Active" />
            ) : (
              <Badge status="default" text="Inactive" />
            )}
          </Space>
        }
        extra={
          <Space>
            <Tag color="blue">{server.tool_count} tools</Tag>
            <Tag>{server.active_tool_count} active</Tag>
            <Dropdown menu={{ items: menuItems }} trigger={['click']}>
              <Button type="text" icon={<MoreOutlined />} />
            </Dropdown>
          </Space>
        }
      >
        <Space direction="vertical" style={{ width: '100%' }} size="small">
          {/* Server info */}
          <div>
            <Text type="secondary">Base URL:</Text>{' '}
            <Text code>{server.base_url}</Text>
          </div>
          {server.description && (
            <Paragraph type="secondary" style={{ marginBottom: 8 }}>
              {server.description}
            </Paragraph>
          )}

          {/* Tools */}
          <Collapse
            activeKey={isExpanded ? ['tools'] : []}
            onChange={(keys) => {
              if (keys.includes('tools')) {
                setExpandedServers([...expandedServers, server.id]);
              } else {
                setExpandedServers(expandedServers.filter((id) => id !== server.id));
              }
            }}
            ghost
          >
            <Panel
              key="tools"
              header={
                <Space>
                  <ToolOutlined />
                  <span>Tools ({server.tool_count})</span>
                </Space>
              }
            >
              {renderToolsTable(server)}
            </Panel>
          </Collapse>
        </Space>
      </Card>
    );
  };

  return (
    <div>
      {/* Header */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <Title level={2} className="mb-2 flex items-center gap-2">
            <CodeOutlined />
            Tool Providers
          </Title>
          <Paragraph type="secondary" className="mb-0">
            Create API-based tool providers with multiple tools. Each provider groups tools
            that share the same base URL and credentials.
          </Paragraph>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadServers} loading={loading}>
            Refresh
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreateServer}
          >
            Create Provider
          </Button>
        </Space>
      </div>

      {/* Info Alert */}
      <Alert
        message="How Tool Providers Work"
        description={
          <div>
            <p className="mb-2">
              Tool Providers let you create API-based tools without writing code:
            </p>
            <ol className="list-decimal list-inside space-y-1 text-sm">
              <li>Create a provider with your API's base URL and credentials</li>
              <li>Add multiple tools, each defining a path and parameters</li>
              <li>Agents call tools by name, the provider makes API calls securely</li>
              <li>Credentials are never exposed to the LLM</li>
            </ol>
          </div>
        }
        type="info"
        showIcon
        className="mb-4"
        closable
      />

      {/* Search */}
      <Input
        placeholder="Search providers and tools..."
        prefix={<SearchOutlined />}
        value={searchText}
        onChange={(e) => setSearchText(e.target.value)}
        style={{ marginBottom: 16, maxWidth: 400 }}
        allowClear
      />

      {/* Content */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 48 }}>
          <Spin size="large" />
        </div>
      ) : filteredServers.length === 0 ? (
        <Card>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              searchText
                ? 'No providers or tools match your search'
                : 'No Tool Providers yet'
            }
          >
            {!searchText && (
              <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateServer}>
                Create Your First Provider
              </Button>
            )}
          </Empty>
        </Card>
      ) : (
        <div>
          {filteredServers.map(renderServerCard)}
        </div>
      )}

      {/* Modal */}
      <DynamicMCPServerModal
        open={modalOpen}
        onClose={() => {
          setModalOpen(false);
          setEditingServer(undefined);
        }}
        onSuccess={loadServers}
        server={editingServer}
        credentials={credentials}
      />
    </div>
  );
};

export default DynamicMCPTools;
