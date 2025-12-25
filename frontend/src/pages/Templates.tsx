import React, { useEffect, useState } from 'react';
import { Row, Col, Spin, Alert, Input, Select, Space, message } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { TemplateCard } from '../components/Templates/TemplateCard';
import { TemplatePreviewModal } from '../components/Templates/TemplatePreviewModal';
import { apiClient } from '../services/api';

const { Search } = Input;
const { Option } = Select;

interface Template {
  id: string;
  name: string;
  description: string;
  category: string;
  tags: string[];
}

export const Templates: React.FC = () => {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [filteredTemplates, setFilteredTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [previewTemplateId, setPreviewTemplateId] = useState<string | null>(null);
  const [previewVisible, setPreviewVisible] = useState(false);

  useEffect(() => {
    fetchTemplates();
  }, []);

  useEffect(() => {
    filterTemplates();
  }, [searchTerm, categoryFilter, templates]);

  const fetchTemplates = async () => {
    try {
      const data = await apiClient.get('/templates');
      setTemplates(data.templates);
      setFilteredTemplates(data.templates);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const filterTemplates = () => {
    let filtered = templates;

    // Filter by category
    if (categoryFilter !== 'all') {
      filtered = filtered.filter((t) => t.category === categoryFilter);
    }

    // Filter by search term
    if (searchTerm) {
      const lowerSearch = searchTerm.toLowerCase();
      filtered = filtered.filter(
        (t) =>
          t.name.toLowerCase().includes(lowerSearch) ||
          t.description.toLowerCase().includes(lowerSearch) ||
          t.tags.some((tag) => tag.toLowerCase().includes(lowerSearch))
      );
    }

    setFilteredTemplates(filtered);
  };

  const handleClone = async (templateId: string) => {
    try {
      const data = await apiClient.post(`/templates/${templateId}/clone`);
      message.success(`Template cloned successfully: ${data.name}`);

      // Navigate to the agent builder with the new agent
      navigate(`/agents/${data.id}/edit`);
    } catch (err) {
      message.error(err instanceof Error ? err.message : 'Failed to clone template');
    }
  };

  const handlePreview = (templateId: string) => {
    setPreviewTemplateId(templateId);
    setPreviewVisible(true);
  };

  const categories = ['all', ...Array.from(new Set(templates.map((t) => t.category)))];

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <Alert message="Error" description={error} type="error" showIcon />
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Agent Templates</h1>
        <p className="text-gray-600">
          Choose from pre-built agent templates to get started quickly
        </p>
      </div>

      <div className="mb-6">
        <Space size="middle" className="w-full" direction="vertical">
          <Search
            placeholder="Search templates..."
            prefix={<SearchOutlined />}
            size="large"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            allowClear
          />
          <Select
            size="large"
            value={categoryFilter}
            onChange={setCategoryFilter}
            style={{ width: 200 }}
          >
            {categories.map((category) => (
              <Option key={category} value={category}>
                {category === 'all'
                  ? 'All Categories'
                  : category.charAt(0).toUpperCase() + category.slice(1)}
              </Option>
            ))}
          </Select>
        </Space>
      </div>

      <Row gutter={[16, 16]}>
        {filteredTemplates.map((template) => (
          <Col key={template.id} xs={24} sm={12} lg={8} xl={6}>
            <TemplateCard
              id={template.id}
              name={template.name}
              description={template.description}
              category={template.category}
              tags={template.tags}
              onClone={handleClone}
              onPreview={handlePreview}
            />
          </Col>
        ))}
      </Row>

      {filteredTemplates.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500">No templates found matching your criteria</p>
        </div>
      )}

      <TemplatePreviewModal
        templateId={previewTemplateId}
        visible={previewVisible}
        onClose={() => setPreviewVisible(false)}
      />
    </div>
  );
};
