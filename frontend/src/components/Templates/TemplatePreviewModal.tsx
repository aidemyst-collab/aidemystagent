import React, { useEffect, useState } from 'react';
import { Modal, Spin, Alert, Descriptions, Tag, Divider } from 'antd';
import ReactFlow, { Background, Controls, MiniMap } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

interface TemplatePreviewModalProps {
  templateId: string | null;
  visible: boolean;
  onClose: () => void;
}

interface TemplateDetails {
  id: string;
  name: string;
  description: string;
  category: string;
  tags: string[];
  config: {
    nodes: any[];
    edges: any[];
  };
}

export const TemplatePreviewModal: React.FC<TemplatePreviewModalProps> = ({
  templateId,
  visible,
  onClose,
}) => {
  const [template, setTemplate] = useState<TemplateDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (templateId && visible) {
      fetchTemplateDetails();
    }
  }, [templateId, visible]);

  const fetchTemplateDetails = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/v1/templates/${templateId}`);
      if (!response.ok) {
        throw new Error('Failed to fetch template details');
      }
      const data = await response.json();
      setTemplate(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="Template Preview"
      open={visible}
      onCancel={onClose}
      width={1000}
      footer={null}
    >
      {loading && (
        <div className="flex justify-center py-8">
          <Spin size="large" />
        </div>
      )}

      {error && (
        <Alert message="Error" description={error} type="error" showIcon />
      )}

      {template && !loading && (
        <div>
          <Descriptions column={1} bordered>
            <Descriptions.Item label="Name">{template.name}</Descriptions.Item>
            <Descriptions.Item label="Description">
              {template.description}
            </Descriptions.Item>
            <Descriptions.Item label="Category">
              <Tag color="blue">{template.category}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Tags">
              {template.tags.map((tag) => (
                <Tag key={tag}>{tag}</Tag>
              ))}
            </Descriptions.Item>
          </Descriptions>

          <Divider>Workflow Preview</Divider>

          <div style={{ height: '400px', border: '1px solid #d9d9d9' }}>
            <ReactFlow
              nodes={template.config.nodes}
              edges={template.config.edges}
              fitView
              nodesDraggable={false}
              nodesConnectable={false}
              elementsSelectable={false}
            >
              <Background />
              <Controls showInteractive={false} />
              <MiniMap />
            </ReactFlow>
          </div>
        </div>
      )}
    </Modal>
  );
};
