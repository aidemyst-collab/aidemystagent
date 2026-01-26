import { useState } from 'react';
import { Modal, Form, Input, Button, Typography, Alert, Spin } from 'antd';
import { PlayCircleOutlined } from '@ant-design/icons';
import { useAuthStore } from '../../features/auth/authStore';

const { TextArea } = Input;
const { Title, Text } = Typography;

interface ToolTesterProps {
  visible: boolean;
  toolName: string;
  toolDescription: string;
  onClose: () => void;
}

export const ToolTester = ({ visible, toolName, toolDescription, onClose }: ToolTesterProps) => {
  const [form] = Form.useForm();
  const [isExecuting, setIsExecuting] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const getToolParameters = (name: string) => {
    const parametersByTool: Record<string, any[]> = {
      calculator: [
        {
          name: 'expression',
          label: 'Mathematical Expression',
          placeholder: '2 + 2 * 3',
          required: true,
        },
      ],
      datetime: [
        {
          name: 'operation',
          label: 'Operation',
          placeholder: 'current',
          required: false,
        },
        {
          name: 'timezone',
          label: 'Timezone',
          placeholder: 'UTC',
          required: false,
        },
      ],
      json_parser: [
        {
          name: 'operation',
          label: 'Operation',
          placeholder: 'parse',
          required: false,
        },
        {
          name: 'json_string',
          label: 'JSON String',
          placeholder: '{"key": "value"}',
          required: true,
          multiline: true,
        },
        {
          name: 'path',
          label: 'Path (for extract)',
          placeholder: 'key.subkey',
          required: false,
        },
      ],
      web_search: [
        {
          name: 'query',
          label: 'Search Query',
          placeholder: 'latest AI developments',
          required: true,
        },
        {
          name: 'max_results',
          label: 'Max Results',
          placeholder: '5',
          required: false,
        },
      ],
    };

    return parametersByTool[name] || [];
  };

  const handleExecute = async () => {
    try {
      await form.validateFields();
      const values = form.getFieldsValue();

      setIsExecuting(true);
      setResult(null);
      setError(null);

      const { tokens } = useAuthStore.getState();
      const response = await fetch(`/api/v1/tools/built-in/${toolName}/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${tokens?.accessToken}`,
        },
        body: JSON.stringify({ input_data: values }),
      });

      const data = await response.json();

      if (data.success) {
        setResult(data.result);
      } else {
        setError(data.error || 'Tool execution failed');
      }
    } catch (err: any) {
      setError(err.message || 'An error occurred');
    } finally {
      setIsExecuting(false);
    }
  };

  const parameters = getToolParameters(toolName);

  return (
    <Modal
      title={
        <div>
          <Title level={4} style={{ margin: 0 }}>
            Test Tool: {toolName}
          </Title>
          <Text type="secondary">{toolDescription}</Text>
        </div>
      }
      open={visible}
      onCancel={onClose}
      width={600}
      footer={null}
    >
      <Form form={form} layout="vertical" className="mt-4">
        {parameters.map((param) => (
          <Form.Item
            key={param.name}
            name={param.name}
            label={param.label}
            rules={[{ required: param.required, message: `${param.label} is required` }]}
          >
            {param.multiline ? (
              <TextArea
                placeholder={param.placeholder}
                rows={4}
              />
            ) : (
              <Input placeholder={param.placeholder} />
            )}
          </Form.Item>
        ))}

        <Form.Item>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={handleExecute}
            loading={isExecuting}
            block
          >
            Execute Tool
          </Button>
        </Form.Item>

        {error && (
          <Alert
            message="Error"
            description={error}
            type="error"
            showIcon
            className="mb-4"
          />
        )}

        {result !== null && (
          <Alert
            message="Result"
            description={
              <pre className="mt-2 p-2 bg-gray-50 rounded overflow-auto max-h-64">
                {JSON.stringify(result, null, 2)}
              </pre>
            }
            type="success"
            showIcon
          />
        )}

        {isExecuting && (
          <div className="text-center">
            <Spin tip="Executing tool..." />
          </div>
        )}
      </Form>
    </Modal>
  );
};
