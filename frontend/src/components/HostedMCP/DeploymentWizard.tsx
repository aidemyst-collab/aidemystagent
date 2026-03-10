import { useState } from 'react';
import {
  Modal,
  Tabs,
  Form,
  Input,
  InputNumber,
  Button,
  Space,
  Typography,
  Divider,
  Alert,
  message,
} from 'antd';
import {
  CloudOutlined,
  GithubOutlined,
  AppstoreOutlined,
  MinusCircleOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  hostedMcpServerService,
  type HostedMCPServerCreateRequest,
  type HostedMCPServerSourceType,
} from '../../features/hosted-mcp/hostedMcpServerService';

const { Text } = Typography;
const { TextArea } = Input;

interface DeploymentWizardProps {
  visible: boolean;
  onClose: () => void;
}

export const DeploymentWizard = ({ visible, onClose }: DeploymentWizardProps) => {
  const [form] = Form.useForm();
  const [activeTab, setActiveTab] = useState<HostedMCPServerSourceType>('docker');
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: (data: HostedMCPServerCreateRequest) =>
      hostedMcpServerService.createServer(data),
    onSuccess: () => {
      message.success('Server deployment started');
      queryClient.invalidateQueries({ queryKey: ['hosted-mcp-servers'] });
      handleClose();
    },
    onError: (error: any) => {
      message.error(error.message || 'Failed to create server');
    },
  });

  const handleClose = () => {
    form.resetFields();
    setActiveTab('docker');
    onClose();
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      // Build source_config based on active tab
      let sourceConfig: any = {};
      if (activeTab === 'docker') {
        sourceConfig = {
          image: values.docker_image,
          registry_credential_id: values.docker_registry_credential_id || undefined,
        };
      } else if (activeTab === 'registry') {
        sourceConfig = {
          package: values.registry_package,
          version: values.registry_version || 'latest',
        };
      } else if (activeTab === 'github') {
        sourceConfig = {
          repo: values.github_repo,
          branch: values.github_branch || 'main',
          dockerfile_path: values.github_dockerfile_path || 'Dockerfile',
        };
      }

      // Build environment variables from form array
      const envVars: Record<string, string> = {};
      if (values.env_vars) {
        values.env_vars.forEach((item: { key: string; value: string }) => {
          if (item.key && item.value) {
            envVars[item.key] = item.value;
          }
        });
      }

      const request: HostedMCPServerCreateRequest = {
        name: values.name,
        description: values.description,
        source_type: activeTab,
        source_config: sourceConfig,
        environment_variables: Object.keys(envVars).length > 0 ? envVars : undefined,
        port: values.port || 3000,
        cpu_cores: values.cpu_cores || 0.25,
        memory_gb: values.memory_gb || 0.5,
        min_replicas: values.min_replicas ?? 0,
        max_replicas: values.max_replicas || 3,
      };

      createMutation.mutate(request);
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  const tabItems = [
    {
      key: 'docker',
      label: (
        <span>
          <CloudOutlined /> Docker Image
        </span>
      ),
      children: (
        <div className="py-4">
          <Alert
            type="info"
            message="Deploy from a pre-built Docker image"
            description="Provide a Docker image URL from Docker Hub, GitHub Container Registry, or any public registry."
            className="mb-4"
            showIcon
          />
          <Form.Item
            name="docker_image"
            label="Docker Image"
            rules={[{ required: activeTab === 'docker', message: 'Please enter a Docker image URL' }]}
          >
            <Input placeholder="ghcr.io/anthropic/mcp-weather:latest" />
          </Form.Item>
          <Form.Item
            name="docker_registry_credential_id"
            label="Registry Credential (Optional)"
            extra="Required for private registries"
          >
            <Input placeholder="credential-id-for-private-registry" />
          </Form.Item>
        </div>
      ),
    },
    {
      key: 'registry',
      label: (
        <span>
          <AppstoreOutlined /> npm Registry
        </span>
      ),
      children: (
        <div className="py-4">
          <Alert
            type="info"
            message="Deploy from npm package"
            description="Install and run an MCP server from the npm registry (e.g., @anthropic/mcp-weather)."
            className="mb-4"
            showIcon
          />
          <Form.Item
            name="registry_package"
            label="npm Package"
            rules={[{ required: activeTab === 'registry', message: 'Please enter a package name' }]}
          >
            <Input placeholder="@anthropic/mcp-weather" />
          </Form.Item>
          <Form.Item
            name="registry_version"
            label="Version"
            initialValue="latest"
          >
            <Input placeholder="latest" />
          </Form.Item>
        </div>
      ),
    },
    {
      key: 'github',
      label: (
        <span>
          <GithubOutlined /> GitHub
        </span>
      ),
      children: (
        <div className="py-4">
          <Alert
            type="info"
            message="Build from GitHub repository"
            description="Build and deploy an MCP server from a public GitHub repository with a Dockerfile."
            className="mb-4"
            showIcon
          />
          <Form.Item
            name="github_repo"
            label="Repository"
            rules={[{ required: activeTab === 'github', message: 'Please enter a GitHub repo' }]}
          >
            <Input placeholder="user/mcp-server-repo" />
          </Form.Item>
          <Form.Item
            name="github_branch"
            label="Branch"
            initialValue="main"
          >
            <Input placeholder="main" />
          </Form.Item>
          <Form.Item
            name="github_dockerfile_path"
            label="Dockerfile Path"
            initialValue="Dockerfile"
          >
            <Input placeholder="Dockerfile" />
          </Form.Item>
        </div>
      ),
    },
  ];

  return (
    <Modal
      title="Deploy Hosted MCP Server"
      open={visible}
      onCancel={handleClose}
      width={700}
      footer={[
        <Button key="cancel" onClick={handleClose}>
          Cancel
        </Button>,
        <Button
          key="deploy"
          type="primary"
          onClick={handleSubmit}
          loading={createMutation.isPending}
        >
          Deploy Server
        </Button>,
      ]}
      destroyOnClose
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          port: 3000,
          cpu_cores: 0.25,
          memory_gb: 0.5,
          min_replicas: 0,
          max_replicas: 3,
        }}
      >
        {/* Server Details */}
        <Form.Item
          name="name"
          label="Server Name"
          rules={[
            { required: true, message: 'Please enter a server name' },
            { max: 100, message: 'Name cannot exceed 100 characters' },
          ]}
        >
          <Input placeholder="My MCP Server" />
        </Form.Item>

        <Form.Item
          name="description"
          label="Description"
        >
          <TextArea rows={2} placeholder="Optional description of this MCP server" />
        </Form.Item>

        <Divider>Source Configuration</Divider>

        {/* Source Type Tabs */}
        <Tabs
          activeKey={activeTab}
          onChange={(key) => setActiveTab(key as HostedMCPServerSourceType)}
          items={tabItems}
        />

        <Divider>Environment Variables</Divider>

        {/* Environment Variables */}
        <Form.List name="env_vars">
          {(fields, { add, remove }) => (
            <>
              {fields.map(({ key, name, ...restField }) => (
                <Space key={key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                  <Form.Item
                    {...restField}
                    name={[name, 'key']}
                    rules={[{ required: true, message: 'Missing key' }]}
                  >
                    <Input placeholder="KEY" style={{ width: 200 }} />
                  </Form.Item>
                  <Form.Item
                    {...restField}
                    name={[name, 'value']}
                    rules={[{ required: true, message: 'Missing value' }]}
                  >
                    <Input placeholder="value" style={{ width: 300 }} />
                  </Form.Item>
                  <MinusCircleOutlined onClick={() => remove(name)} />
                </Space>
              ))}
              <Form.Item>
                <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
                  Add Environment Variable
                </Button>
              </Form.Item>
            </>
          )}
        </Form.List>

        <Text type="secondary" className="text-xs block mb-4">
          Tip: Use {'{{credential:name}}'} to reference stored credentials securely
        </Text>

        <Divider>Resource Configuration</Divider>

        {/* Resource Settings */}
        <div className="grid grid-cols-2 gap-4">
          <Form.Item
            name="port"
            label="Container Port"
            rules={[{ required: true, message: 'Please enter a port' }]}
          >
            <InputNumber min={1} max={65535} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="cpu_cores"
            label="CPU Cores"
            rules={[{ required: true, message: 'Please enter CPU cores' }]}
          >
            <InputNumber min={0.25} max={4} step={0.25} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="memory_gb"
            label="Memory (GB)"
            rules={[{ required: true, message: 'Please enter memory' }]}
          >
            <InputNumber min={0.5} max={8} step={0.5} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="min_replicas"
            label="Min Replicas"
            extra="Set to 0 for scale-to-zero"
          >
            <InputNumber min={0} max={10} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="max_replicas"
            label="Max Replicas"
          >
            <InputNumber min={1} max={10} style={{ width: '100%' }} />
          </Form.Item>
        </div>
      </Form>
    </Modal>
  );
};

export default DeploymentWizard;
