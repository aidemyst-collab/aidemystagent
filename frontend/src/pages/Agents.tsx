import { Typography, Button, Table, Tag, Space, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, RocketOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useWorkflows, useDeleteWorkflow } from '../features/workflows/workflowHooks';
import type { Workflow } from '../types/workflow';

const { Title } = Typography;

export const Agents = () => {
  const navigate = useNavigate();
  const { data: workflows, isLoading } = useWorkflows();
  const deleteWorkflow = useDeleteWorkflow();

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: Workflow) => (
        <a onClick={() => navigate(`/agents/${record.id}/edit`)}>{text}</a>
      ),
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      render: (text: string) => text || '-',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'deployed' ? 'green' : status === 'draft' ? 'blue' : 'default'}>
          {status.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Version',
      dataIndex: 'version',
      key: 'version',
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleDateString(),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: any, record: Workflow) => (
        <Space size="middle">
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => navigate(`/agents/${record.id}/edit`)}
          >
            Edit
          </Button>
          <Button
            type="link"
            icon={<RocketOutlined />}
            onClick={() => navigate(`/agents/${record.id}/test`)}
          >
            Test
          </Button>
          <Popconfirm
            title="Delete workflow"
            description="Are you sure you want to delete this workflow?"
            onConfirm={() => deleteWorkflow.mutate(record.id)}
            okText="Yes"
            cancelText="No"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <Title level={2}>Workflows</Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate('/agents/new')}
        >
          New Workflow
        </Button>
      </div>

      {workflows && workflows.length > 0 ? (
        <Table
          columns={columns}
          dataSource={workflows}
          rowKey="id"
          loading={isLoading}
        />
      ) : (
        <p className="text-gray-600">No workflows created yet. Create your first workflow to get started.</p>
      )}
    </div>
  );
};
