import React, { useState } from 'react';
import { Modal, Form, Select, Input, Switch, message } from 'antd';

const { Option } = Select;
const { TextArea } = Input;

interface DeploymentModalProps {
  visible: boolean;
  agentId: string;
  agentName: string;
  onClose: () => void;
  onSuccess: () => void;
}

export const DeploymentModal: React.FC<DeploymentModalProps> = ({
  visible,
  agentId,
  agentName,
  onClose,
  onSuccess,
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      const response = await fetch('/api/v1/deployments', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          agent_id: agentId,
          version: values.version,
          environment: values.environment,
          config: {
            auto_scale: values.auto_scale,
            max_concurrent: values.max_concurrent,
            timeout: values.timeout,
          },
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create deployment');
      }

      message.success('Deployment created successfully');
      form.resetFields();
      onSuccess();
      onClose();
    } catch (err) {
      message.error(err instanceof Error ? err.message : 'Failed to create deployment');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={`Deploy Agent: ${agentName}`}
      open={visible}
      onCancel={onClose}
      onOk={handleSubmit}
      confirmLoading={loading}
      width={600}
    >
      <Form form={form} layout="vertical" initialValues={{ environment: 'development', auto_scale: true, max_concurrent: 10, timeout: 300 }}>
        <Form.Item
          name="version"
          label="Version"
          rules={[{ required: true, message: 'Please enter version' }]}
        >
          <Input placeholder="e.g., 1.0.0, v2.1.3" />
        </Form.Item>

        <Form.Item
          name="environment"
          label="Environment"
          rules={[{ required: true, message: 'Please select environment' }]}
        >
          <Select>
            <Option value="development">Development</Option>
            <Option value="staging">Staging</Option>
            <Option value="production">Production</Option>
          </Select>
        </Form.Item>

        <Form.Item name="auto_scale" label="Auto-scaling" valuePropName="checked">
          <Switch />
        </Form.Item>

        <Form.Item
          name="max_concurrent"
          label="Max Concurrent Requests"
          rules={[{ required: true, message: 'Please enter max concurrent requests' }]}
        >
          <Input type="number" min={1} max={100} />
        </Form.Item>

        <Form.Item
          name="timeout"
          label="Timeout (seconds)"
          rules={[{ required: true, message: 'Please enter timeout' }]}
        >
          <Input type="number" min={30} max={900} />
        </Form.Item>
      </Form>
    </Modal>
  );
};
