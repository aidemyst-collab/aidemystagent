import { useState, useRef, useEffect } from 'react';
import { Card, Input, Button, Typography, Divider, Tag, Spin, Select, Alert, Tooltip } from 'antd';
import { SendOutlined, ClockCircleOutlined, ThunderboltOutlined, ReloadOutlined } from '@ant-design/icons';
import { workflowService } from '../../features/workflows/workflowService';

const { TextArea } = Input;
const { Title, Text } = Typography;

type InputMode = 'chat' | 'json' | 'form';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface PlaygroundProps {
  agentId: string;
  agentName: string;
  defaultMode?: InputMode;
}

// Generate a random session ID
const generateSessionId = () => {
  return `session_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
};

export const AgentPlayground = ({ agentId, agentName, defaultMode = 'chat' }: PlaygroundProps) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [inputMode, setInputMode] = useState<InputMode>(defaultMode);
  const [jsonInput, setJsonInput] = useState('{}');
  const [isLoading, setIsLoading] = useState(false);
  const [executionTime, setExecutionTime] = useState<number | null>(null);
  const [tokensUsed, setTokensUsed] = useState<number | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState(generateSessionId());
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    setValidationError(null);

    // Get input based on mode
    let inputValue: any;
    let displayContent: string;

    try {
      if (inputMode === 'chat') {
        if (!input.trim()) return;
        inputValue = input;
        displayContent = input;
      } else if (inputMode === 'json') {
        if (!jsonInput.trim()) return;
        inputValue = JSON.parse(jsonInput);
        displayContent = jsonInput;
      } else {
        // form mode - not implemented in this simple version
        if (!jsonInput.trim()) return;
        inputValue = JSON.parse(jsonInput);
        displayContent = jsonInput;
      }
    } catch (error) {
      setValidationError('Invalid JSON format');
      return;
    }

    if (isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: displayContent,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setJsonInput('{}');
    setIsLoading(true);

    try {
      const startTime = performance.now();

      // Use the workflow service to execute the agent
      const data = await workflowService.executeWorkflow(agentId, typeof inputValue === 'string' ? inputValue : JSON.stringify(inputValue));

      const endTime = performance.now();

      // Check if validation failed
      if (data.input_metadata && !data.input_metadata.validation_passed) {
        const errorMsg = data.input_metadata.error || 'Input validation failed';
        setValidationError(errorMsg);

        const errorMessage: Message = {
          role: 'assistant',
          content: `Validation Error: ${errorMsg}`,
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, errorMessage]);
      } else {
        const assistantMessage: Message = {
          role: 'assistant',
          content: data.output || 'No response',
          timestamp: new Date(),
        };

        setMessages(prev => [...prev, assistantMessage]);
        setExecutionTime(Math.round(endTime - startTime));
        setTokensUsed(data.tokens_used || 0);
      }
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

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewSession = () => {
    setSessionId(generateSessionId());
    setMessages([]);
    setInput('');
    setJsonInput('{}');
    setExecutionTime(null);
    setTokensUsed(null);
    setValidationError(null);
  };

  return (
    <div className="h-full flex flex-col">
      <Card
        title={
          <div className="flex justify-between items-center">
            <Title level={4} style={{ margin: 0 }}>
              {agentName} - Test Playground
            </Title>
            <div className="flex gap-2 items-center">
              <Tooltip title="Current session ID for conversation memory">
                <Tag color="purple" style={{ cursor: 'pointer' }}>
                  Session: {sessionId.substring(0, 16)}...
                </Tag>
              </Tooltip>
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
              <Tooltip title="Start a new conversation session">
                <Button
                  type="text"
                  icon={<ReloadOutlined />}
                  onClick={handleNewSession}
                  size="small"
                >
                  New Session
                </Button>
              </Tooltip>
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
          <div className="mb-3 flex items-center gap-2">
            <Text strong>Input Mode:</Text>
            <Select
              value={inputMode}
              onChange={(value) => setInputMode(value)}
              style={{ width: 150 }}
              options={[
                { label: 'Chat', value: 'chat' },
                { label: 'JSON', value: 'json' },
                { label: 'Form', value: 'form' },
              ]}
            />
          </div>

          {validationError && (
            <Alert
              message={validationError}
              type="error"
              closable
              onClose={() => setValidationError(null)}
              style={{ marginBottom: 12 }}
            />
          )}

          <div className="flex gap-2">
            {inputMode === 'chat' ? (
              <TextArea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type your message here... (Shift+Enter for new line)"
                autoSize={{ minRows: 2, maxRows: 4 }}
                disabled={isLoading}
              />
            ) : (
              <TextArea
                value={jsonInput}
                onChange={(e) => setJsonInput(e.target.value)}
                placeholder={
                  inputMode === 'json'
                    ? '{\n  "key": "value"\n}'
                    : '{\n  "field1": "value1",\n  "field2": "value2"\n}'
                }
                autoSize={{ minRows: 4, maxRows: 8 }}
                disabled={isLoading}
                style={{ fontFamily: 'monospace' }}
              />
            )}
            <Button
              type="primary"
              icon={isLoading ? <Spin size="small" /> : <SendOutlined />}
              onClick={handleSend}
              disabled={isLoading || (inputMode === 'chat' ? !input.trim() : !jsonInput.trim())}
              size="large"
            >
              Send
            </Button>
          </div>

          <Text type="secondary" style={{ fontSize: 11, marginTop: 8, display: 'block' }}>
            {inputMode === 'chat' && 'Conversational text input'}
            {inputMode === 'json' && 'Structured JSON data with schema validation'}
            {inputMode === 'form' && 'Form data as JSON object'}
          </Text>
        </div>
      </Card>
    </div>
  );
};
