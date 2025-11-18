import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Tabs, Typography } from 'antd';
import { ThunderboltOutlined, ApiOutlined } from '@ant-design/icons';
import { AgentPlayground } from '../components/Testing/AgentPlayground';
import { StreamingPlayground } from '../components/Testing/StreamingPlayground';

const { Title } = Typography;

export const AgentTest = () => {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState('standard');

  // In production, fetch agent details
  const agentName = 'Test Agent';

  return (
    <div>
      <Title level={2}>Test Agent</Title>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'standard',
            label: (
              <span>
                <ThunderboltOutlined />
                Standard Mode
              </span>
            ),
            children: id ? (
              <AgentPlayground agentId={id} agentName={agentName} />
            ) : (
              <div>No agent selected</div>
            ),
          },
          {
            key: 'streaming',
            label: (
              <span>
                <ApiOutlined />
                Streaming Mode
              </span>
            ),
            children: id ? (
              <StreamingPlayground agentId={id} agentName={agentName} />
            ) : (
              <div>No agent selected</div>
            ),
          },
        ]}
      />
    </div>
  );
};
