import { Card, Typography } from 'antd';
import {
  LoginOutlined,
  RobotOutlined,
  DatabaseOutlined,
  BranchesOutlined,
  ToolOutlined,
  ExportOutlined,
  ApartmentOutlined,
  PlayCircleOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  AudioOutlined,
  SoundOutlined,
  CodeOutlined,
  PhoneOutlined,
  MessageOutlined,
  SendOutlined,
} from '@ant-design/icons';
import type { NodeType } from '../../types/workflow';

const { Title, Text } = Typography;

interface NodeDefinition {
  type: NodeType;
  label: string;
  icon: React.ReactNode;
  color: string;
  description: string;
}

const nodeDefinitions: NodeDefinition[] = [
  {
    type: 'INPUT',
    label: 'Input',
    icon: <LoginOutlined />,
    color: '#52c41a',
    description: 'Entry point for user requests',
  },
  {
    type: 'MEMORY',
    label: 'Memory',
    icon: <DatabaseOutlined />,
    color: '#fa8c16',
    description: 'Store and retrieve conversation history',
  },
  {
    type: 'LLM_AGENT',
    label: 'LLM Agent',
    icon: <RobotOutlined />,
    color: '#1890ff',
    description: 'Core language model agent',
  },
  {
    type: 'RAG_RETRIEVER',
    label: 'RAG Retriever',
    icon: <DatabaseOutlined />,
    color: '#722ed1',
    description: 'Retrieve knowledge from RAG system',
  },
  {
    type: 'DECISION',
    label: 'Decision',
    icon: <BranchesOutlined />,
    color: '#fa8c16',
    description: 'Conditional logic and routing',
  },
  {
    type: 'TOOL',
    label: 'Tool',
    icon: <ToolOutlined />,
    color: '#13c2c2',
    description: 'Execute specific tools',
  },
  {
    type: 'OUTPUT',
    label: 'Output',
    icon: <ExportOutlined />,
    color: '#f5222d',
    description: 'Final response formatting',
  },
  {
    type: 'EXECUTE_WORKFLOW',
    label: 'Execute Workflow',
    icon: <PlayCircleOutlined />,
    color: '#8B5CF6',
    description: 'Call and execute another workflow',
  },
  {
    type: 'SUBGRAPH',
    label: 'Subgraph',
    icon: <ApartmentOutlined />,
    color: '#eb2f96',
    description: 'Nested agent workflow (legacy)',
  },
  {
    type: 'FILE_READER',
    label: 'File Reader',
    icon: <FileTextOutlined />,
    color: '#3B82F6',
    description: 'Read files from disk',
  },
  {
    type: 'STRUCTURED_OUTPUT_PARSER',
    label: 'Parser',
    icon: <CheckCircleOutlined />,
    color: '#9333EA',
    description: 'Parse and validate LLM output to JSON',
  },
  {
    type: 'AUDIO_TO_TEXT',
    label: 'Audio to Text',
    icon: <AudioOutlined />,
    color: '#9333EA',
    description: 'Transcribe audio to text (Twilio, Whisper)',
  },
  {
    type: 'TEXT_TO_AUDIO',
    label: 'Text to Audio',
    icon: <SoundOutlined />,
    color: '#059669',
    description: 'Convert text to speech (TTS)',
  },
  {
    type: 'CODE',
    label: 'Code',
    icon: <CodeOutlined />,
    color: '#F59E0B',
    description: 'Execute custom JavaScript or Python code',
  },
  {
    type: 'VOICE_INPUT',
    label: 'Voice Input',
    icon: <PhoneOutlined />,
    color: '#10B981',
    description: 'Receive incoming voice calls (Twilio/Etisalat)',
  },
  {
    type: 'VOICE_OUTPUT',
    label: 'Voice Output',
    icon: <SoundOutlined />,
    color: '#3B82F6',
    description: 'Play audio response to caller',
  },
  {
    type: 'WHATSAPP_INPUT',
    label: 'WhatsApp Input',
    icon: <MessageOutlined />,
    color: '#25D366',
    description: 'Receive WhatsApp messages (Meta Cloud API)',
  },
  {
    type: 'WHATSAPP_OUTPUT',
    label: 'WhatsApp Output',
    icon: <SendOutlined />,
    color: '#128C7E',
    description: 'Send WhatsApp responses (text, media, templates)',
  },
];

export const NodeLibrary = () => {
  const onDragStart = (event: React.DragEvent, nodeType: NodeType, label: string) => {
    event.dataTransfer.setData('application/reactflow', JSON.stringify({ nodeType, label }));
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className="p-4 bg-gray-50 h-full overflow-auto">
      <Title level={5}>Node Library</Title>
      <Text type="secondary" className="block mb-4">
        Drag nodes to the canvas
      </Text>

      <div className="space-y-2">
        {nodeDefinitions.map((node) => (
          <Card
            key={node.type}
            size="small"
            draggable
            onDragStart={(e) => onDragStart(e, node.type, node.label)}
            className="cursor-move hover:shadow-md transition-shadow"
            style={{ borderLeft: `3px solid ${node.color}` }}
          >
            <div className="flex items-center gap-2">
              <div style={{ color: node.color, fontSize: 18 }}>{node.icon}</div>
              <div>
                <div className="font-medium">{node.label}</div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {node.description}
                </Text>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
};
