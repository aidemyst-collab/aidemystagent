import { Typography, Button } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Title } = Typography;

export const Agents = () => {
  const navigate = useNavigate();

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <Title level={2}>Agents</Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate('/agents/new')}
        >
          New Agent
        </Button>
      </div>
      <p className="text-gray-600">No agents created yet. Create your first agent to get started.</p>
    </div>
  );
};
