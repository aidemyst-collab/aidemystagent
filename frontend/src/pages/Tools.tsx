import { useState, useEffect } from 'react';
import { Typography, Row, Col, Tabs, Spin, Empty, Button, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { ToolCard } from '../components/Tools/ToolCard';
import { ToolTester } from '../components/Tools/ToolTester';
import { ToolCreationModal } from '../components/Tools/ToolCreationModal';
import { toolService, type Tool as CustomTool } from '../features/tools/toolService';

const { Title } = Typography;

interface Tool {
  name: string;
  description: string;
  schema: any;
}

export const Tools = () => {
  const [builtInTools, setBuiltInTools] = useState<Tool[]>([]);
  const [customTools, setCustomTools] = useState<CustomTool[]>([]);
  const [apiTools, setApiTools] = useState<CustomTool[]>([]);
  const [mcpTools, setMcpTools] = useState<CustomTool[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);
  const [testerVisible, setTesterVisible] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editingTool, setEditingTool] = useState<CustomTool | null>(null);
  const [selectedToolType, setSelectedToolType] = useState<string | null>(null);

  useEffect(() => {
    fetchAllTools();
  }, []);

  const fetchAllTools = async () => {
    setLoading(true);
    try {
      await Promise.all([
        fetchBuiltInTools(),
        fetchCustomTools(),
      ]);
    } catch (error) {
      console.error('Error fetching tools:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchBuiltInTools = async () => {
    try {
      const data = await toolService.getBuiltInTools();
      setBuiltInTools(data.tools || []);
    } catch (error) {
      console.error('Error fetching built-in tools:', error);
    }
  };

  const fetchCustomTools = async () => {
    try {
      const data = await toolService.getTools();
      const tools = data.tools || [];

      // Separate tools by type
      setCustomTools(tools.filter(t => t.type === 'custom'));
      setApiTools(tools.filter(t => t.type === 'api'));
      setMcpTools(tools.filter(t => t.type === 'mcp'));
    } catch (error) {
      console.error('Error fetching custom tools:', error);
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

  const handleCreateTool = (toolType: string | null = null) => {
    setEditingTool(null);
    setSelectedToolType(toolType);
    setCreateModalVisible(true);
  };

  const handleEditTool = (tool: CustomTool) => {
    setEditingTool(tool);
    setCreateModalVisible(true);
  };

  const handleDeleteTool = async (toolId: string) => {
    try {
      await toolService.deleteTool(toolId);
      message.success('Tool deleted successfully');
      fetchCustomTools();
    } catch (error) {
      console.error('Error deleting tool:', error);
      message.error('Failed to delete tool');
    }
  };

  const handleModalSuccess = () => {
    fetchCustomTools();
  };

  const renderToolGrid = (tools: CustomTool[], category: string, toolType: string) => {
    return (
      <div>
        <div className="flex justify-end mb-4">
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => handleCreateTool(toolType)}
          >
            Create {category} Tool
          </Button>
        </div>
        {tools.length === 0 ? (
          <Empty description={`No ${category.toLowerCase()} tools created yet`} />
        ) : (
          <Row gutter={[16, 16]}>
            {tools.map((tool) => (
              <Col key={tool.id} xs={24} sm={12} lg={8} xl={6}>
                <ToolCard
                  name={tool.name}
                  description={tool.description}
                  category={category}
                  onTest={() => handleTest({ name: tool.name, description: tool.description, schema: {} })}
                  onDetails={() => handleDetails({ name: tool.name, description: tool.description, schema: {} })}
                  onEdit={() => handleEditTool(tool)}
                  onDelete={() => handleDeleteTool(tool.id)}
                />
              </Col>
            ))}
          </Row>
        )}
      </div>
    );
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
      <div className="mb-6">
        <Title level={2} className="mb-2">Tools</Title>
        <p className="text-gray-600">
          Browse and test available tools for your agents
        </p>
      </div>

      <Tabs
        defaultActiveKey="built-in"
        items={[
          {
            key: 'built-in',
            label: `Built-in Tools (${builtInTools.length})`,
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
            label: `Custom Tools (${customTools.length})`,
            children: renderToolGrid(customTools, 'Custom', 'custom'),
          },
          {
            key: 'api',
            label: `API Integration (${apiTools.length})`,
            children: renderToolGrid(apiTools, 'API', 'api'),
          },
          {
            key: 'mcp',
            label: `MCP Tools (${mcpTools.length})`,
            children: renderToolGrid(mcpTools, 'MCP', 'mcp'),
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

      <ToolCreationModal
        visible={createModalVisible}
        onClose={() => {
          setCreateModalVisible(false);
          setEditingTool(null);
          setSelectedToolType(null);
        }}
        onSuccess={handleModalSuccess}
        initialData={editingTool}
        preSelectedType={selectedToolType}
      />
    </div>
  );
};
