import { useState } from 'react';
import {
  Typography,
  Button,
  Table,
  Tag,
  Space,
  message,
  Popconfirm,
  Tooltip,
  Switch,
  Empty,
  Card,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  ApiOutlined,
  EditOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  CodeOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { DynamicMCPToolModal } from '../components/MCPTools/DynamicMCPToolModal';
import {
  mcpToolService,
  type DynamicMCPTool,
} from '../features/mcp-tools/mcpToolService';

const { Title, Text, Paragraph } = Typography;

const methodColors: Record<string, string> = {
  GET: 'green',
  POST: 'blue',
  PUT: 'orange',
  PATCH: 'purple',
  DELETE: 'red',
};

export const DynamicMCPTools = () => {
  const [modalVisible, setModalVisible] = useState(false);
  const [editingTool, setEditingTool] = useState<DynamicMCPTool | null>(null);

  const queryClient = useQueryClient();

  // Fetch tools
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['dynamic-mcp-tools'],
    queryFn: () => mcpToolService.getTools(0, 100, false), // Include inactive
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (toolId: string) => mcpToolService.deleteTool(toolId),
    onSuccess: () => {
      message.success('Tool deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['dynamic-mcp-tools'] });
    },
    onError: (error: any) => {
      message.error(error.message || 'Failed to delete tool');
    },
  });

  // Toggle mutation
  const toggleMutation = useMutation({
    mutationFn: (toolId: string) => mcpToolService.toggleTool(toolId),
    onSuccess: (data) => {
      message.success(`Tool ${data.is_active ? 'activated' : 'deactivated'}`);
      queryClient.invalidateQueries({ queryKey: ['dynamic-mcp-tools'] });
    },
    onError: (error: any) => {
      message.error(error.message || 'Failed to toggle tool');
    },
  });

  // Refresh server mutation
  const refreshMutation = useMutation({
    mutationFn: () => mcpToolService.refreshServer(),
    onSuccess: () => {
      message.success('Dynamic MCP Server notified to reload tools');
    },
    onError: (error: any) => {
      message.error(error.message || 'Failed to notify server');
    },
  });

  const handleCreateTool = () => {
    setEditingTool(null);
    setModalVisible(true);
  };

  const handleEditTool = (tool: DynamicMCPTool) => {
    setEditingTool(tool);
    setModalVisible(true);
  };

  const handleDeleteTool = (toolId: string) => {
    deleteMutation.mutate(toolId);
  };

  const handleToggleTool = (toolId: string) => {
    toggleMutation.mutate(toolId);
  };

  const tools = data?.tools || [];

  const columns = [
    {
      title: 'Tool Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: DynamicMCPTool) => (
        <Space>
          <ApiOutlined style={{ color: '#6366f1' }} />
          <Text strong>{name}</Text>
          {!record.is_active && <Tag color="default">Inactive</Tag>}
        </Space>
      ),
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      width: 300,
    },
    {
      title: 'Method',
      dataIndex: 'method',
      key: 'method',
      width: 100,
      render: (method: string) => (
        <Tag color={methodColors[method] || 'default'}>{method}</Tag>
      ),
    },
    {
      title: 'Endpoint',
      dataIndex: 'api_endpoint',
      key: 'api_endpoint',
      ellipsis: true,
      width: 250,
      render: (endpoint: string) => (
        <Tooltip title={endpoint}>
          <Text code className="text-xs">
            {endpoint.length > 40 ? endpoint.substring(0, 40) + '...' : endpoint}
          </Text>
        </Tooltip>
      ),
    },
    {
      title: 'Parameters',
      key: 'parameters',
      width: 100,
      render: (_: any, record: DynamicMCPTool) => (
        <Tag>{record.parameters?.length || 0} params</Tag>
      ),
    },
    {
      title: 'Status',
      key: 'status',
      width: 100,
      render: (_: any, record: DynamicMCPTool) => (
        <Switch
          checked={record.is_active}
          onChange={() => handleToggleTool(record.id)}
          loading={toggleMutation.isPending}
          checkedChildren={<CheckCircleOutlined />}
          unCheckedChildren={<CloseCircleOutlined />}
        />
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 100,
      render: (_: any, record: DynamicMCPTool) => (
        <Space>
          <Tooltip title="Edit">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEditTool(record)}
            />
          </Tooltip>
          <Popconfirm
            title="Delete this tool?"
            description="This action cannot be undone."
            onConfirm={() => handleDeleteTool(record.id)}
            okText="Delete"
            cancelText="Cancel"
            okButtonProps={{ danger: true }}
          >
            <Tooltip title="Delete">
              <Button type="text" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* Header */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <Title level={2} className="mb-2 flex items-center gap-2">
            <CodeOutlined />
            Dynamic MCP Tools
          </Title>
          <Paragraph type="secondary" className="mb-0">
            Create API-based tools that agents can use. These tools are exposed via the Dynamic MCP Server.
          </Paragraph>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
            Refresh
          </Button>
          <Button
            onClick={() => refreshMutation.mutate()}
            loading={refreshMutation.isPending}
          >
            Sync to MCP Server
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateTool}>
            Create Tool
          </Button>
        </Space>
      </div>

      {/* Info Alert */}
      <Alert
        message="How Dynamic MCP Tools Work"
        description={
          <div>
            <p className="mb-2">
              Dynamic MCP Tools let you create API-based tools without writing code:
            </p>
            <ol className="list-decimal list-inside space-y-1 text-sm">
              <li>Define your tool with an API endpoint and parameters</li>
              <li>Agents call the tool by name with the required parameters</li>
              <li>The Dynamic MCP Server makes the actual API call securely</li>
              <li>The response is returned to the agent</li>
            </ol>
          </div>
        }
        type="info"
        showIcon
        className="mb-4"
        closable
      />

      {/* Tools Table */}
      {tools.length === 0 && !isLoading ? (
        <Card>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <div className="text-center">
                <Text type="secondary">No dynamic MCP tools created yet</Text>
                <br />
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={handleCreateTool}
                  className="mt-4"
                >
                  Create Your First Tool
                </Button>
              </div>
            }
          />
        </Card>
      ) : (
        <Table
          columns={columns}
          dataSource={tools}
          rowKey="id"
          loading={isLoading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} tools`,
          }}
        />
      )}

      {/* Create/Edit Modal */}
      <DynamicMCPToolModal
        visible={modalVisible}
        onClose={() => {
          setModalVisible(false);
          setEditingTool(null);
        }}
        editingTool={editingTool}
      />
    </div>
  );
};
