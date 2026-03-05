import { useEffect } from 'react';
import { Modal, Form, Input, Select, message } from 'antd';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import {
  mcpServerService,
  type MCPServer,
  type MCPServerCreateRequest,
  type MCPServerUpdateRequest,
} from '../../features/mcp-servers/mcpServerService';
import { apiClient } from '../../services/api';

const { TextArea } = Input;

interface MCPServerModalProps {
  visible: boolean;
  onClose: () => void;
  editingServer?: MCPServer | null;
}

interface Credential {
  id: string;
  name: string;
  provider: string;
}

export const MCPServerModal = ({
  visible,
  onClose,
  editingServer,
}: MCPServerModalProps) => {
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const isEditing = !!editingServer;

  // Fetch credentials for dropdown
  const { data: credentialsData } = useQuery({
    queryKey: ['credentials'],
    queryFn: () => apiClient.get<{ credentials: Credential[] }>('/credentials'),
    enabled: visible,
  });

  // Reset form when modal opens/closes or editingServer changes
  useEffect(() => {
    if (visible) {
      if (editingServer) {
        form.setFieldsValue({
          name: editingServer.name,
          description: editingServer.description || '',
          server_url: editingServer.server_url,
          transport_type: editingServer.transport_type,
          credential_id: editingServer.credential_id || undefined,
        });
      } else {
        form.resetFields();
        form.setFieldsValue({
          transport_type: 'sse',
        });
      }
    }
  }, [visible, editingServer, form]);

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: MCPServerCreateRequest) => mcpServerService.createServer(data),
    onSuccess: () => {
      message.success('MCP server created successfully');
      queryClient.invalidateQueries({ queryKey: ['mcp-servers'] });
      onClose();
    },
    onError: (error: any) => {
      message.error(error.message || 'Failed to create MCP server');
    },
  });

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: MCPServerUpdateRequest }) =>
      mcpServerService.updateServer(id, data),
    onSuccess: () => {
      message.success('MCP server updated successfully');
      queryClient.invalidateQueries({ queryKey: ['mcp-servers'] });
      onClose();
    },
    onError: (error: any) => {
      message.error(error.message || 'Failed to update MCP server');
    },
  });

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      // Clean up empty strings
      const data = {
        ...values,
        description: values.description || undefined,
        credential_id: values.credential_id || undefined,
      };

      if (isEditing && editingServer) {
        updateMutation.mutate({ id: editingServer.id, data });
      } else {
        createMutation.mutate(data);
      }
    } catch (error) {
      // Form validation error - handled by Form component
    }
  };

  const isLoading = createMutation.isPending || updateMutation.isPending;

  return (
    <Modal
      title={isEditing ? 'Edit MCP Server' : 'Add MCP Server'}
      open={visible}
      onCancel={onClose}
      onOk={handleSubmit}
      okText={isEditing ? 'Save Changes' : 'Add Server'}
      confirmLoading={isLoading}
      destroyOnClose
      width={560}
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          transport_type: 'sse',
        }}
      >
        <Form.Item
          name="name"
          label="Server Name"
          rules={[
            { required: true, message: 'Please enter a server name' },
            { max: 100, message: 'Name must be 100 characters or less' },
          ]}
        >
          <Input placeholder="e.g., Production MCP Server" />
        </Form.Item>

        <Form.Item
          name="description"
          label="Description"
          rules={[{ max: 500, message: 'Description must be 500 characters or less' }]}
        >
          <TextArea
            rows={2}
            placeholder="Optional description of this MCP server"
          />
        </Form.Item>

        <Form.Item
          name="server_url"
          label="Server URL"
          rules={[
            { required: true, message: 'Please enter the server URL' },
            {
              pattern: /^https?:\/\/.+/,
              message: 'URL must start with http:// or https://',
            },
          ]}
          extra="The MCP server endpoint (e.g., http://localhost:3000/sse)"
        >
          <Input placeholder="https://mcp-server.example.com/sse" />
        </Form.Item>

        <Form.Item
          name="transport_type"
          label="Transport Type"
          rules={[{ required: true, message: 'Please select a transport type' }]}
          extra="SSE is recommended for most MCP servers"
        >
          <Select>
            <Select.Option value="sse">
              <div className="flex items-center gap-2">
                <span>SSE</span>
                <span className="text-gray-400 text-xs">
                  (Server-Sent Events - Recommended)
                </span>
              </div>
            </Select.Option>
            <Select.Option value="http">
              <div className="flex items-center gap-2">
                <span>HTTP</span>
                <span className="text-gray-400 text-xs">(Streamable HTTP)</span>
              </div>
            </Select.Option>
            <Select.Option value="stdio">
              <div className="flex items-center gap-2">
                <span>STDIO</span>
                <span className="text-gray-400 text-xs">(Standard I/O)</span>
              </div>
            </Select.Option>
          </Select>
        </Form.Item>

        <Form.Item
          name="credential_id"
          label="Authentication Credential"
          extra="Optional credential for authenticating with the MCP server"
        >
          <Select
            allowClear
            placeholder="Select a credential (optional)"
            options={[
              { label: 'No authentication', value: '' },
              ...(credentialsData?.credentials || []).map((cred) => ({
                label: `${cred.name} (${cred.provider})`,
                value: cred.id,
              })),
            ]}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
};
