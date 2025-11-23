import { Typography, Card, Row, Col, Statistic, List, Button, Space, Tag, Skeleton, Empty } from 'antd';
import { RocketOutlined, PlayCircleOutlined, CheckCircleOutlined, PlusOutlined, AppstoreOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { useDashboardStats, useRecentActivity } from '../features/dashboard/dashboardHooks';
import { useAgents } from '../features/agents/agentHooks';
import { useNavigate } from 'react-router-dom';
import type { RecentActivity } from '../features/dashboard/dashboardService';

const { Title, Text, Paragraph } = Typography;

const getActivityIcon = (type: RecentActivity['type']) => {
  switch (type) {
    case 'agent_created':
      return <PlusOutlined style={{ color: '#52c41a' }} />;
    case 'agent_deployed':
      return <RocketOutlined style={{ color: '#1890ff' }} />;
    case 'agent_executed':
      return <ThunderboltOutlined style={{ color: '#faad14' }} />;
    default:
      return <PlayCircleOutlined />;
  }
};

const getActivityText = (activity: RecentActivity) => {
  switch (activity.type) {
    case 'agent_created':
      return `Created agent "${activity.agentName}"`;
    case 'agent_deployed':
      return `Deployed agent "${activity.agentName}"`;
    case 'agent_executed':
      return `Executed agent "${activity.agentName}"`;
    default:
      return activity.type;
  }
};

const formatTimestamp = (timestamp: string) => {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${diffDays}d ago`;
};

export const Dashboard = () => {
  const navigate = useNavigate();
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: activity, isLoading: activityLoading } = useRecentActivity(5);
  const { data: agents, isLoading: agentsLoading } = useAgents();

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ marginBottom: 8 }}>Dashboard</Title>
        <Text type="secondary">Welcome back! Here's what's happening with your agents.</Text>
      </div>

      {/* Statistics Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Agents"
              value={statsLoading ? 0 : (agents?.length || 0)}
              prefix={<RocketOutlined />}
              loading={statsLoading || agentsLoading}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Deployed"
              value={statsLoading ? 0 : (stats?.deployedAgents || 0)}
              prefix={<CheckCircleOutlined />}
              loading={statsLoading}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Executions"
              value={statsLoading ? 0 : (stats?.totalExecutions || 0)}
              prefix={<PlayCircleOutlined />}
              loading={statsLoading}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Today"
              value={statsLoading ? 0 : (stats?.executionsToday || 0)}
              prefix={<ThunderboltOutlined />}
              suffix={`/ ${stats?.executionsThisWeek || 0} week`}
              loading={statsLoading}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* Quick Actions */}
        <Col xs={24} lg={12}>
          <Card
            title="Quick Actions"
            extra={<AppstoreOutlined />}
          >
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <Button
                type="primary"
                icon={<PlusOutlined />}
                size="large"
                block
                onClick={() => navigate('/agents/builder')}
              >
                Create New Agent
              </Button>
              <Button
                icon={<RocketOutlined />}
                size="large"
                block
                onClick={() => navigate('/agents')}
              >
                View All Agents
              </Button>
              <Button
                icon={<AppstoreOutlined />}
                size="large"
                block
                onClick={() => navigate('/templates')}
              >
                Browse Templates
              </Button>
            </Space>

            {agents && agents.length === 0 && (
              <div style={{ marginTop: 16, padding: 12, background: '#f0f5ff', borderRadius: 4 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  💡 <strong>Get Started:</strong> Create your first AI agent to automate workflows and enhance productivity.
                </Text>
              </div>
            )}
          </Card>
        </Col>

        {/* Recent Activity */}
        <Col xs={24} lg={12}>
          <Card
            title="Recent Activity"
            extra={<PlayCircleOutlined />}
          >
            {activityLoading ? (
              <Skeleton active paragraph={{ rows: 4 }} />
            ) : activity && activity.length > 0 ? (
              <List
                dataSource={activity}
                renderItem={(item) => (
                  <List.Item style={{ padding: '12px 0' }}>
                    <List.Item.Meta
                      avatar={getActivityIcon(item.type)}
                      title={
                        <Text style={{ fontSize: 14 }}>
                          {getActivityText(item)}
                        </Text>
                      }
                      description={
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {formatTimestamp(item.timestamp)}
                        </Text>
                      }
                    />
                  </List.Item>
                )}
              />
            ) : (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="No recent activity"
                style={{ padding: '20px 0' }}
              />
            )}

            {activity && activity.length > 0 && (
              <Button type="link" block style={{ marginTop: 8 }}>
                View all activity
              </Button>
            )}
          </Card>
        </Col>
      </Row>

      {/* Recent Agents */}
      {agents && agents.length > 0 && (
        <Card
          title="Recent Agents"
          extra={
            <Button type="link" onClick={() => navigate('/agents')}>
              View all
            </Button>
          }
          style={{ marginTop: 16 }}
        >
          <List
            dataSource={agents.slice(0, 5)}
            renderItem={(agent) => (
              <List.Item
                actions={[
                  <Tag color={agent.status === 'deployed' ? 'green' : 'default'}>
                    {agent.status}
                  </Tag>,
                  <Button type="link" onClick={() => navigate(`/agents/${agent.id}`)}>
                    View
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  title={agent.name}
                  description={agent.description || 'No description'}
                />
              </List.Item>
            )}
          />
        </Card>
      )}
    </div>
  );
};
