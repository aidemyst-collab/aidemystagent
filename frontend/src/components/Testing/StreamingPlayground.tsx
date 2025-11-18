import { useState, useRef, useEffect } from 'react';
import { Card, Input, Button, Typography, Divider, Tag, Spin, Steps } from 'antd';
import { SendOutlined, ThunderboltOutlined, NodeIndexOutlined } from '@ant-design/icons';

const { TextArea } = Input;
const { Title, Text } = Typography;

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

interface StreamingPlaygroundProps {
  agentId: string;
  agentName: string;
}

export const StreamingPlayground = ({ agentId, agentName }: StreamingPlaygroundProps) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [executionPath, setExecutionPath] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsStreaming(true);
    setExecutionPath([]);

    // Create empty assistant message for streaming
    const assistantMessage: Message = {
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
    };
    setMessages(prev => [...prev, assistantMessage]);

    try {
      const response = await fetch(`/api/v1/execute/${agentId}/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ input: input, stream: true }),
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error('No reader available');

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.substring(6));

            if (data.type === 'step') {
              setExecutionPath(prev => [...prev, data.node]);
            } else if (data.type === 'token') {
              setMessages(prev => {
                const newMessages = [...prev];
                const lastMessage = newMessages[newMessages.length - 1];
                if (lastMessage && lastMessage.role === 'assistant') {
                  lastMessage.content += data.content;
                }
                return newMessages;
              });
            } else if (data.type === 'complete') {
              setMessages(prev => {
                const newMessages = [...prev];
                const lastMessage = newMessages[newMessages.length - 1];
                if (lastMessage) {
                  lastMessage.isStreaming = false;
                }
                return newMessages;
              });
            }
          }
        }
      }
    } catch (error) {
      console.error('Error streaming agent:', error);
      setMessages(prev => {
        const newMessages = [...prev];
        newMessages[newMessages.length - 1] = {
          role: 'assistant',
          content: 'Error streaming response. Please try again.',
          timestamp: new Date(),
        };
        return newMessages;
      });
    } finally {
      setIsStreaming(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="h-full flex gap-4">
      {/* Main Chat Area */}
      <div className="flex-1">
        <Card
          title={
            <Title level={4} style={{ margin: 0 }}>
              {agentName} - Streaming Test
            </Title>
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
                        {message.isStreaming && <span className="animate-pulse">▊</span>}
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
                placeholder="Type your message here..."
                autoSize={{ minRows: 2, maxRows: 4 }}
                disabled={isStreaming}
              />
              <Button
                type="primary"
                icon={isStreaming ? <Spin size="small" /> : <SendOutlined />}
                onClick={handleSend}
                disabled={!input.trim() || isStreaming}
                size="large"
              >
                {isStreaming ? 'Sending...' : 'Send'}
              </Button>
            </div>
          </div>
        </Card>
      </div>

      {/* Execution Path Panel */}
      <div style={{ width: 300 }}>
        <Card
          title={
            <div className="flex items-center gap-2">
              <NodeIndexOutlined />
              <Text strong>Execution Path</Text>
            </div>
          }
          size="small"
        >
          {executionPath.length === 0 ? (
            <Text type="secondary">No execution yet</Text>
          ) : (
            <Steps
              direction="vertical"
              size="small"
              current={executionPath.length - 1}
              items={executionPath.map((node, index) => ({
                title: node,
                description: `Step ${index + 1}`,
              }))}
            />
          )}
        </Card>
      </div>
    </div>
  );
};
