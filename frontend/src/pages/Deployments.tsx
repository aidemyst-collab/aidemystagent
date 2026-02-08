import React, { useEffect, useState } from 'react';
import {
  Row,
  Col,
  Spin,
  Alert,
  Select,
  Space,
  message,
  Empty,
  Button,
} from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { DeploymentCard } from '../components/Deployments/DeploymentCard';
import { DeploymentModal } from '../components/Deployments/DeploymentModal';
import { apiClient } from '../services/api';

const { Option } = Select;

interface Deployment {
  id: string;
  agent_id: string;
  agent_name: string;
  version: string;
  environment: string;
  status: string;
  endpoint_url?: string;
  api_key?: string;
  deployed_at?: string;
}

interface Agent {
  id: string;
  name: string;
}

export const Deployments: React.FC = () => {
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [environmentFilter, setEnvironmentFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [modalVisible, setModalVisible] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      // Fetch deployments and agents in parallel
      const [deploymentsData, agentsData] = await Promise.all([
        apiClient.get('/deployments'),
        apiClient.get('/agents'),
      ]);

      setDeployments(deploymentsData.deployments);
      setAgents(agentsData.agents);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async (id: string) => {
    try {
      await apiClient.post(`/deployments/${id}/stop`);
      message.success('Deployment stopped successfully');
      fetchData();
    } catch (err) {
      message.error(err instanceof Error ? err.message : 'Failed to stop deployment');
    }
  };

  const handleRestart = async (id: string) => {
    try {
      await apiClient.post(`/deployments/${id}/restart`);
      message.success('Deployment restarted successfully');
      fetchData();
    } catch (err) {
      message.error(
        err instanceof Error ? err.message : 'Failed to restart deployment'
      );
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await apiClient.delete(`/deployments/${id}`);
      message.success('Deployment deleted successfully');
      fetchData();
    } catch (err) {
      message.error(
        err instanceof Error ? err.message : 'Failed to delete deployment'
      );
    }
  };

  const handleExport = async (id: string) => {
    try {
      const exportData = await apiClient.get(`/deployments/${id}/export`);

      // Create and download JSON file
      const blob = new Blob([JSON.stringify(exportData, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `deployment-${id}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      message.success('Deployment exported successfully');
    } catch (err) {
      message.error(
        err instanceof Error ? err.message : 'Failed to export deployment'
      );
    }
  };

  const openDeployModal = (agent: Agent) => {
    setSelectedAgent(agent);
    setModalVisible(true);
  };

  const filteredDeployments = deployments.filter((d) => {
    if (environmentFilter !== 'all' && d.environment !== environmentFilter) {
      return false;
    }
    if (statusFilter !== 'all' && d.status !== statusFilter) {
      return false;
    }
    return true;
  });

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
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold mb-2">Deployments</h1>
          <p className="text-gray-600">Manage your agent deployments</p>
        </div>
        <Select
          placeholder="Select agent to deploy"
          style={{ width: 300 }}
          onChange={(value) => {
            const agent = agents.find((a) => a.id === value);
            if (agent) openDeployModal(agent);
          }}
        >
          {agents.map((agent) => (
            <Option key={agent.id} value={agent.id}>
              <PlusOutlined /> Deploy {agent.name}
            </Option>
          ))}
        </Select>
      </div>

      <div className="mb-6">
        <Space>
          <Select
            value={environmentFilter}
            onChange={setEnvironmentFilter}
            style={{ width: 200 }}
          >
            <Option value="all">All Environments</Option>
            <Option value="development">Development</Option>
            <Option value="staging">Staging</Option>
            <Option value="production">Production</Option>
          </Select>

          <Select value={statusFilter} onChange={setStatusFilter} style={{ width: 200 }}>
            <Option value="all">All Statuses</Option>
            <Option value="active">Active</Option>
            <Option value="stopped">Stopped</Option>
            <Option value="failed">Failed</Option>
            <Option value="pending">Pending</Option>
          </Select>
        </Space>
      </div>

      {filteredDeployments.length === 0 ? (
        <Empty description="No deployments found" />
      ) : (
        <Row gutter={[16, 16]}>
          {filteredDeployments.map((deployment) => (
            <Col key={deployment.id} xs={24} sm={12} lg={8}>
              <DeploymentCard
                id={deployment.id}
                agentName={deployment.agent_name || 'Unknown Agent'}
                version={deployment.version}
                environment={deployment.environment}
                status={deployment.status}
                endpointUrl={deployment.endpoint_url}
                apiKey={deployment.api_key}
                deployedAt={deployment.deployed_at}
                onStop={handleStop}
                onRestart={handleRestart}
                onDelete={handleDelete}
                onExport={handleExport}
              />
            </Col>
          ))}
        </Row>
      )}

      {selectedAgent && (
        <DeploymentModal
          visible={modalVisible}
          agentId={selectedAgent.id}
          agentName={selectedAgent.name}
          onClose={() => setModalVisible(false)}
          onSuccess={fetchData}
        />
      )}
    </div>
  );
};
