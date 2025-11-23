import { Form, Input, Card, Typography, Empty, InputNumber, Select } from 'antd';
import { useEffect } from 'react';
import { Node } from '@xyflow/react';

const { Title } = Typography;
const { TextArea } = Input;

interface PropertyPanelProps {
  selectedNode: Node | null;
  onUpdate: (nodeId: string, data: any) => void;
}

export const PropertyPanel = ({ selectedNode, onUpdate }: PropertyPanelProps) => {
  const [form] = Form.useForm();

  useEffect(() => {
    if (selectedNode) {
      form.setFieldsValue(selectedNode.data);
    } else {
      form.resetFields();
    }
  }, [selectedNode, form]);

  if (!selectedNode) {
    return (
      <div className="p-4 h-full flex items-center justify-center">
        <Empty description="Select a node to edit properties" />
      </div>
    );
  }

  const handleValueChange = (changedValues: any) => {
    if (selectedNode) {
      onUpdate(selectedNode.id, { ...selectedNode.data, ...changedValues });
    }
  };

  return (
    <div className="p-4 bg-gray-50 h-full overflow-auto">
      <Title level={5}>Properties</Title>
      <Card size="small" className="mb-4">
        <div className="text-sm text-gray-600">Node ID: {selectedNode.id}</div>
        <div className="text-sm text-gray-600">Type: {selectedNode.data.type}</div>
      </Card>

      <Form
        form={form}
        layout="vertical"
        onValuesChange={handleValueChange}
        size="small"
      >
        <Form.Item name="label" label="Label">
          <Input placeholder="Node label" />
        </Form.Item>

        {selectedNode.data.type === 'LLM_AGENT' && (
          <>
            <Form.Item name={['config', 'model']} label="Model">
              <Select
                options={[
                  { label: 'GPT-4', value: 'gpt-4' },
                  { label: 'GPT-3.5 Turbo', value: 'gpt-3.5-turbo' },
                  { label: 'Claude 3 Opus', value: 'claude-3-opus' },
                  { label: 'Claude 3 Sonnet', value: 'claude-3-sonnet' },
                ]}
                placeholder="Select model"
              />
            </Form.Item>

            <Form.Item name={['config', 'temperature']} label="Temperature">
              <InputNumber
                min={0}
                max={2}
                step={0.1}
                style={{ width: '100%' }}
                placeholder="0.7"
              />
            </Form.Item>

            <Form.Item name={['config', 'maxTokens']} label="Max Tokens">
              <InputNumber
                min={1}
                max={4096}
                style={{ width: '100%' }}
                placeholder="2048"
              />
            </Form.Item>

            <Form.Item name={['config', 'systemPrompt']} label="System Prompt">
              <TextArea rows={4} placeholder="Enter system prompt..." />
            </Form.Item>
          </>
        )}

        {selectedNode.data.type === 'RAG_RETRIEVER' && (
          <>
            <Form.Item name={['config', 'topK']} label="Top K Results">
              <InputNumber
                min={1}
                max={20}
                style={{ width: '100%' }}
                placeholder="5"
              />
            </Form.Item>

            <Form.Item name={['config', 'scoreThreshold']} label="Score Threshold">
              <InputNumber
                min={0}
                max={1}
                step={0.1}
                style={{ width: '100%' }}
                placeholder="0.7"
              />
            </Form.Item>
          </>
        )}

        {selectedNode.data.type === 'TOOL' && (
          <Form.Item name={['config', 'toolId']} label="Tool">
            <Select
              placeholder="Select tool"
              options={[
                { label: 'Web Search', value: 'web_search' },
                { label: 'Calculator', value: 'calculator' },
                { label: 'Date/Time', value: 'datetime' },
              ]}
            />
          </Form.Item>
        )}

        {selectedNode.data.type === 'DECISION' && (
          <Form.Item name={['config', 'condition']} label="Condition">
            <TextArea rows={3} placeholder="Enter condition logic..." />
          </Form.Item>
        )}
      </Form>
    </div>
  );
};
