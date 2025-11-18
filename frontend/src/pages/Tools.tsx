import { useState, useEffect } from 'react';
import { Typography, Row, Col, Tabs, Spin, Empty } from 'antd';
import { ToolCard } from '../components/Tools/ToolCard';
import { ToolTester } from '../components/Tools/ToolTester';

const { Title } = Typography;

interface Tool {
  name: string;
  description: string;
  schema: any;
}

export const Tools = () => {
  const [builtInTools, setBuiltInTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);
  const [testerVisible, setTesterVisible] = useState(false);

  useEffect(() => {
    fetchBuiltInTools();
  }, []);

  const fetchBuiltInTools = async () => {
    try {
      const response = await fetch('/api/v1/tools/built-in');
      const data = await response.json();
      setBuiltInTools(data.tools || []);
    } catch (error) {
      console.error('Error fetching tools:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTest = (tool: Tool) => {
    setSelectedTool(tool);
    setTesterVisible(true);
  };

  const handleDetails = (tool: Tool) => {
    console.log('Tool details:', tool);
    // TODO: Show tool details modal
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <Title level={2}>Tools</Title>
      <p className="text-gray-600 mb-6">
        Browse and test available tools for your agents
      </p>

      <Tabs
        defaultActiveKey="built-in"
        items={[
          {
            key: 'built-in',
            label: 'Built-in Tools',
            children: (
              <>
                {builtInTools.length === 0 ? (
                  <Empty description="No built-in tools available" />
                ) : (
                  <Row gutter={[16, 16]}>
                    {builtInTools.map((tool) => (
                      <Col key={tool.name} xs={24} sm={12} lg={8} xl={6}>
                        <ToolCard
                          name={tool.name}
                          description={tool.description}
                          category="Built-in"
                          onTest={() => handleTest(tool)}
                          onDetails={() => handleDetails(tool)}
                        />
                      </Col>
                    ))}
                  </Row>
                )}
              </>
            ),
          },
          {
            key: 'custom',
            label: 'Custom Tools',
            children: (
              <Empty description="No custom tools created yet" />
            ),
          },
          {
            key: 'api',
            label: 'API Integration Tools',
            children: (
              <Empty description="No API integration tools configured" />
            ),
          },
        ]}
      />

      {selectedTool && (
        <ToolTester
          visible={testerVisible}
          toolName={selectedTool.name}
          toolDescription={selectedTool.description}
          onClose={() => {
            setTesterVisible(false);
            setSelectedTool(null);
          }}
        />
      )}
    </div>
  );
};
