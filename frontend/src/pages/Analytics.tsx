import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Spin, Alert, Select, DatePicker } from 'antd';
import {
  RocketOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import type { Dayjs } from 'dayjs';
import { apiClient } from '../services/api';

const { RangePicker } = DatePicker;
const { Option } = Select;

interface AnalyticsData {
  total_agents: number;
  total_executions: number;
  avg_execution_time: number;
  success_rate: number;
  executions_by_agent: Array<{ agent_name: string; count: number }>;
  executions_over_time: Array<{ date: string; count: number }>;
}

export const Analytics: React.FC = () => {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<string>('all');
  const [dateRange, setDateRange] = useState<[Dayjs | null, Dayjs | null] | null>(
    null
  );

  useEffect(() => {
    fetchAnalytics();
  }, [selectedAgent, dateRange]);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      // Build query parameters
      const params = new URLSearchParams();
      if (selectedAgent !== 'all') {
        params.append('agent_id', selectedAgent);
      }
      if (dateRange && dateRange[0] && dateRange[1]) {
        params.append('start_date', dateRange[0].toISOString());
        params.append('end_date', dateRange[1].toISOString());
      }

      const analyticsData = await apiClient.get(`/analytics?${params}`);
      setData(analyticsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  if (loading && !data) {
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
        <h1 className="text-3xl font-bold mb-2">Analytics Dashboard</h1>
        <p className="text-gray-600">Monitor your agent performance and usage</p>
      </div>

      <div className="mb-6 flex gap-4">
        <Select
          value={selectedAgent}
          onChange={setSelectedAgent}
          style={{ width: 200 }}
        >
          <Option value="all">All Agents</Option>
          {/* TODO: Load agents from API */}
        </Select>

        <RangePicker
          onChange={(dates) => setDateRange(dates)}
          style={{ width: 300 }}
        />
      </div>

      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Agents"
              value={data?.total_agents || 0}
              prefix={<RocketOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Executions"
              value={data?.total_executions || 0}
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Avg Execution Time"
              value={data?.avg_execution_time || 0}
              suffix="ms"
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Success Rate"
              value={data?.success_rate || 0}
              suffix="%"
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="Executions by Agent" className="h-full">
            {data?.executions_by_agent && data.executions_by_agent.length > 0 ? (
              <div className="space-y-2">
                {data.executions_by_agent.map((item, index) => (
                  <div key={index} className="flex justify-between items-center">
                    <span>{item.agent_name}</span>
                    <span className="font-bold text-blue-600">{item.count}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500">No data available</p>
            )}
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="Executions Over Time" className="h-full">
            {data?.executions_over_time &&
            data.executions_over_time.length > 0 ? (
              <div className="space-y-2">
                {data.executions_over_time.map((item, index) => (
                  <div key={index} className="flex justify-between items-center">
                    <span>{new Date(item.date).toLocaleDateString()}</span>
                    <span className="font-bold text-green-600">{item.count}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500">No data available</p>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};
