import { Typography, Card, Row, Col, Statistic } from 'antd';
import { RocketOutlined, ToolOutlined, PlayCircleOutlined, UserOutlined } from '@ant-design/icons';

const { Title } = Typography;

export const Dashboard = () => {
  return (
    <div>
      <Title level={2}>Dashboard</Title>
      <p className="text-gray-600 mb-6">Welcome to AgentStudio</p>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Agents"
              value={0}
              prefix={<RocketOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Active Tools"
              value={0}
              prefix={<ToolOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Executions"
              value={0}
              prefix={<PlayCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Users"
              value={0}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card className="mt-6">
        <Title level={4}>Quick Start</Title>
        <p>Get started by creating your first AI agent or exploring templates.</p>
      </Card>
    </div>
  );
};
