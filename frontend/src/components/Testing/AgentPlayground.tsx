import { useState, useRef, useEffect } from 'react';
import { Card, Input, Button, Typography, Divider, Tag, Spin } from 'antd';
import { SendOutlined, ClockCircleOutlined, ThunderboltOutlined } from '@ant-design/icons';

const { TextArea } = Input;
const { Title, Text } = Typography;

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface PlaygroundProps {
  agentId: string;
  agentName: string;
}

export const AgentPlayground = ({ agentId, agentName }: PlaygroundProps) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [executionTime, setExecutionTime] = useState<number | null>(null);
  const [tokensUsed, setTokensUsed] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const startTime = performance.now();

      const response = await fetch(`/api/v1/execute/${agentId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ input: input }),
      });

      const data = await response.json();
      const endTime = performance.now();

      const assistantMessage: Message = {
        role: 'assistant',
        content: data.output || 'No response',
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);
      setExecutionTime(Math.round(endTime - startTime));
      setTokensUsed(data.tokens_used || 0);
    } catch (error) {
      console.error('Error executing agent:', error);
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Error executing agent. Please try again.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="h-full flex flex-col">
      <Card
        title={
          <div className="flex justify-between items-center">
            <Title level={4} style={{ margin: 0 }}>
              {agentName} - Test Playground
            </Title>
            <div className="flex gap-2">
              {executionTime !== null && (
                <Tag icon={<ClockCircleOutlined />} color="blue">
                  {executionTime}ms
                </Tag>
              )}
              {tokensUsed !== null && (
                <Tag icon={<ThunderboltOutlined />} color="green">
                  {tokensUsed} tokens
                </Tag>
              )}
            </div>
          </div>
        }
        style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
        bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 0 }}
      >
        {/* Messages Area */}
        <div
          className="flex-1 overflow-y-auto p-4 bg-gray-50"
          style={{ minHeight: 400, maxHeight: 600 }}
        >
          {messages.length === 0 ? (
            <div className="text-center text-gray-400 mt-20">
              <Text>Start a conversation by typing a message below</Text>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`flex ${
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  <div
                    className={`max-w-[70%] p-3 rounded-lg ${
                      message.role === 'user'
                        ? 'bg-blue-500 text-white'
                        : 'bg-white border border-gray-200'
                    }`}
                  >
                    <Text
                      style={{
                        color: message.role === 'user' ? 'white' : 'inherit',
                        whiteSpace: 'pre-wrap',
                      }}
                    >
                      {message.content}
                    </Text>
                    <div className="mt-1">
                      <Text
                        type="secondary"
                        style={{
                          fontSize: 11,
                          color: message.role === 'user' ? 'rgba(255,255,255,0.7)' : undefined,
                        }}
                      >
                        {message.timestamp.toLocaleTimeString()}
                      </Text>
                    </div>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <Divider style={{ margin: 0 }} />

        {/* Input Area */}
        <div className="p-4 bg-white">
          <div className="flex gap-2">
            <TextArea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message here... (Shift+Enter for new line)"
              autoSize={{ minRows: 2, maxRows: 4 }}
              disabled={isLoading}
            />
            <Button
              type="primary"
              icon={isLoading ? <Spin size="small" /> : <SendOutlined />}
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              size="large"
            >
              Send
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
};
