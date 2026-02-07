import { useState, useRef, useEffect } from 'react';
import { Card, Input, Button, Typography, Divider, Tag, Spin, Select, Alert, Tooltip, Upload, Progress, Collapse } from 'antd';
import { SendOutlined, ClockCircleOutlined, ThunderboltOutlined, ReloadOutlined, AudioOutlined, UploadOutlined, PauseCircleOutlined, SoundOutlined, BugOutlined, CheckCircleOutlined, CloseCircleOutlined, CodeOutlined } from '@ant-design/icons';
import { workflowService } from '../../features/workflows/workflowService';

const { TextArea } = Input;
const { Title, Text } = Typography;
const { Panel } = Collapse;

type InputMode = 'chat' | 'json' | 'form' | 'audio';

interface ExecutionTraceEntry {
  node_id: string;
  node_type: string;
  node_label?: string;
  input_data?: Record<string, any>;
  output_data?: Record<string, any>;
  status: 'success' | 'error' | 'skipped';
  error?: string;
  duration_ms?: number;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  audioData?: string; // Base64 audio for playback
  audioFormat?: string;
  executionTrace?: ExecutionTraceEntry[];
  executionError?: string;
}

interface PlaygroundProps {
  agentId: string;
  agentName: string;
  defaultMode?: InputMode;
  inputConfig?: any;
  outputConfig?: any;
}

// Generate a random session ID
const generateSessionId = () => {
  return `session_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
};

export const AgentPlayground = ({
  agentId,
  agentName,
  defaultMode = 'chat',
  inputConfig,
  outputConfig
}: PlaygroundProps) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [inputMode, setInputMode] = useState<InputMode>(defaultMode);
  const [jsonInput, setJsonInput] = useState('{}');
  const [isLoading, setIsLoading] = useState(false);
  const [executionTime, setExecutionTime] = useState<number | null>(null);
  const [tokensUsed, setTokensUsed] = useState<number | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState(generateSessionId());
  const [showExecutionLog, setShowExecutionLog] = useState(true);
  const [lastExecutionTrace, setLastExecutionTrace] = useState<ExecutionTraceEntry[]>([]);
  const [lastExecutionError, setLastExecutionError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Audio state
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [recordingTime, setRecordingTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentPlayingIndex, setCurrentPlayingIndex] = useState<number | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Cleanup audio URLs on unmount
  useEffect(() => {
    return () => {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]);

  // Start recording
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        setAudioBlob(audioBlob);
        const url = URL.createObjectURL(audioBlob);
        setAudioUrl(url);

        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);

      // Start timer
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);

    } catch (error) {
      console.error('Error accessing microphone:', error);
      setValidationError('Could not access microphone. Please check permissions.');
    }
  };

  // Stop recording
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);

      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
    }
  };

  // Handle audio file upload
  const handleAudioUpload = (file: File) => {
    setAudioBlob(file);
    const url = URL.createObjectURL(file);
    setAudioUrl(url);
    return false; // Prevent auto upload
  };

  // Convert blob to base64
  const blobToBase64 = (blob: Blob): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64 = (reader.result as string).split(',')[1];
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  };

  // Play audio response
  const playAudio = (audioData: string, format: string, index: number) => {
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
    }

    const audio = new Audio(`data:audio/${format};base64,${audioData}`);
    audioPlayerRef.current = audio;

    audio.onplay = () => {
      setIsPlaying(true);
      setCurrentPlayingIndex(index);
    };

    audio.onended = () => {
      setIsPlaying(false);
      setCurrentPlayingIndex(null);
    };

    audio.onerror = () => {
      setIsPlaying(false);
      setCurrentPlayingIndex(null);
    };

    audio.play();
  };

  // Stop audio playback
  const stopAudio = () => {
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      audioPlayerRef.current.currentTime = 0;
      setIsPlaying(false);
      setCurrentPlayingIndex(null);
    }
  };

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
      } else if (inputMode === 'audio') {
        if (!audioBlob) {
          setValidationError('Please record or upload audio first');
          return;
        }

        // Convert audio to base64
        const audioBase64 = await blobToBase64(audioBlob);
        inputValue = {
          audio_data: audioBase64,
          audio_format: audioBlob.type.includes('webm') ? 'webm' : 'wav',
          input_mode: 'audio'
        };
        displayContent = `🎤 Audio message (${recordingTime || Math.round(audioBlob.size / 1000)}s)`;
      } else {
        // form mode
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
    setAudioBlob(null);
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);
    }
    setRecordingTime(0);
    setIsLoading(true);

    try {
      const startTime = performance.now();

      // Use the workflow service to execute the agent
      const data = await workflowService.executeWorkflow(
        agentId,
        typeof inputValue === 'string' ? inputValue : JSON.stringify(inputValue),
        inputMode,
        sessionId  // Pass session ID for memory persistence
      );

      const endTime = performance.now();

      // Debug: Log the full response
      console.log('=== WORKFLOW EXECUTION RESPONSE ===');
      console.log('Full response:', data);
      console.log('Execution trace:', data.execution_trace);
      console.log('Execution trace length:', data.execution_trace?.length || 0);

      // Log details from LLM_AGENT node
      const llmAgentTrace = data.execution_trace?.find((t: any) => t.node_type === 'LLM_AGENT');
      if (llmAgentTrace) {
        console.log('=== LLM_AGENT INPUT DATA ===');
        console.log('Memory:', llmAgentTrace.input_data?.memory);
        console.log('RAG Retrieval:', llmAgentTrace.input_data?.rag_retrieval);
        console.log('LLM Request:', llmAgentTrace.input_data?.llm_request);
        console.log('=== LLM_AGENT OUTPUT DATA ===');
        console.log('Output:', llmAgentTrace.output_data);
      }
      console.log('===================================');

      // Capture execution trace
      const executionTrace = data.execution_trace || [];
      setLastExecutionTrace(executionTrace);

      // Check for error in response
      if (data.error) {
        setLastExecutionError(data.error);
      } else {
        setLastExecutionError(null);
      }

      // Check if validation failed
      if (data.input_metadata && !data.input_metadata.validation_passed) {
        const errorMsg = data.input_metadata.error || 'Input validation failed';
        setValidationError(errorMsg);
        setLastExecutionError(errorMsg);

        const errorMessage: Message = {
          role: 'assistant',
          content: `Validation Error: ${errorMsg}`,
          timestamp: new Date(),
          executionTrace,
          executionError: errorMsg,
        };
        setMessages(prev => [...prev, errorMessage]);
      } else {
        // Check for errors in execution trace
        const errorNode = executionTrace.find((entry: ExecutionTraceEntry) => entry.status === 'error');
        const traceError = errorNode?.error || null;
        if (traceError) {
          setLastExecutionError(traceError);
        }

        const assistantMessage: Message = {
          role: 'assistant',
          content: data.output || (traceError ? `Error: ${traceError}` : 'No response'),
          timestamp: new Date(),
          audioData: data.audio_data,
          audioFormat: data.audio_format || 'mp3',
          executionTrace,
          executionError: traceError || undefined,
        };

        setMessages(prev => [...prev, assistantMessage]);
        setExecutionTime(Math.round(endTime - startTime));
        setTokensUsed(data.tokens_used || 0);

        // Auto-play audio if configured and audio response is available
        if (data.audio_data && outputConfig?.audioConfig?.autoPlay) {
          setTimeout(() => {
            playAudio(data.audio_data, data.audio_format || 'mp3', messages.length);
          }, 100);
        }
      }
    } catch (error: any) {
      console.error('Error executing agent:', error);

      // Determine error message based on error type
      let errorMsg: string;
      if (error?.message === 'Failed to fetch' || error?.name === 'TypeError') {
        errorMsg = 'Cannot connect to backend server. Please ensure the backend is running on http://localhost:8000';
      } else if (error?.response?.data?.detail) {
        errorMsg = error.response.data.detail;
      } else if (error?.response?.status === 401) {
        errorMsg = 'Authentication failed. Please log in again.';
      } else if (error?.response?.status === 403) {
        errorMsg = 'Permission denied. You do not have access to execute this workflow.';
      } else if (error?.response?.status === 404) {
        errorMsg = 'Workflow not found. It may have been deleted.';
      } else if (error?.response?.status >= 500) {
        errorMsg = `Server error (${error.response.status}): ${error?.response?.data?.detail || 'Internal server error'}`;
      } else {
        errorMsg = error?.message || 'Error executing agent. Please try again.';
      }

      setLastExecutionError(errorMsg);
      setLastExecutionTrace([]);

      const errorMessage: Message = {
        role: 'assistant',
        content: `Error: ${errorMsg}`,
        timestamp: new Date(),
        executionError: errorMsg,
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
    setAudioBlob(null);
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
      setAudioUrl(null);
    }
    setRecordingTime(0);
    setExecutionTime(null);
    setTokensUsed(null);
    setValidationError(null);
    setLastExecutionTrace([]);
    setLastExecutionError(null);
    stopAudio();
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Render node data with proper formatting
  const renderNodeData = (data: Record<string, any> | undefined, maxLength: number = 500) => {
    if (!data || Object.keys(data).length === 0) {
      return <Text type="secondary" italic>No data</Text>;
    }
    try {
      const jsonStr = JSON.stringify(data, null, 2);
      const truncated = jsonStr.length > maxLength ? jsonStr.substring(0, maxLength) + '...' : jsonStr;
      return (
        <pre style={{
          backgroundColor: '#f5f5f5',
          padding: '8px',
          borderRadius: '4px',
          fontSize: '11px',
          maxHeight: '150px',
          overflow: 'auto',
          margin: 0,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}>
          {truncated}
        </pre>
      );
    } catch {
      return <Text type="secondary">Unable to display data</Text>;
    }
  };

  // Get status icon and color for execution trace entry
  const getStatusDisplay = (status: string) => {
    switch (status) {
      case 'success':
        return { icon: <CheckCircleOutlined />, color: '#52c41a', text: 'Success' };
      case 'error':
        return { icon: <CloseCircleOutlined />, color: '#ff4d4f', text: 'Error' };
      case 'skipped':
        return { icon: <ClockCircleOutlined />, color: '#faad14', text: 'Skipped' };
      default:
        return { icon: <ClockCircleOutlined />, color: '#1890ff', text: status };
    }
  };

  // Get node type color
  const getNodeTypeColor = (nodeType: string) => {
    const colors: Record<string, string> = {
      'INPUT': '#1890ff',
      'OUTPUT': '#722ed1',
      'LLM_AGENT': '#13c2c2',
      'RAG_RETRIEVER': '#eb2f96',
      'TOOL': '#fa8c16',
      'DECISION': '#faad14',
      'MEMORY': '#2f54eb',
      'AUDIO_TO_TEXT': '#52c41a',
      'TEXT_TO_AUDIO': '#059669',
      'FILE_READER': '#8c8c8c',
    };
    return colors[nodeType] || '#8c8c8c';
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
              <Tooltip title="Toggle execution log">
                <Button
                  type={showExecutionLog ? 'primary' : 'text'}
                  icon={<BugOutlined />}
                  onClick={() => setShowExecutionLog(!showExecutionLog)}
                  size="small"
                  ghost={showExecutionLog}
                >
                  Debug
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
              <Text>
                {inputMode === 'audio'
                  ? 'Record or upload audio to start the conversation'
                  : 'Start a conversation by typing a message below'}
              </Text>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message, index) => (
                <div
                  key={index}
                  style={{
                    display: 'flex',
                    justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
                  }}
                >
                  <div
                    style={{
                      maxWidth: '70%',
                      padding: '12px',
                      borderRadius: '8px',
                      backgroundColor: message.role === 'user' ? '#1890ff' : '#ffffff',
                      color: message.role === 'user' ? '#ffffff' : 'inherit',
                      border: message.role === 'user' ? 'none' : '1px solid #e8e8e8',
                      boxShadow: '0 1px 2px rgba(0,0,0,0.1)',
                    }}
                  >
                    {/* User label for user messages */}
                    {message.role === 'user' && (
                      <div style={{ fontSize: '11px', opacity: 0.8, marginBottom: '4px' }}>
                        You
                      </div>
                    )}
                    <div
                      style={{
                        color: message.role === 'user' ? '#ffffff' : 'inherit',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                      }}
                    >
                      {message.content}
                    </div>

                    {/* Audio playback for assistant messages */}
                    {message.role === 'assistant' && message.audioData && (
                      <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid #e8e8e8' }}>
                        <Button
                          type="primary"
                          size="small"
                          icon={
                            isPlaying && currentPlayingIndex === index
                              ? <PauseCircleOutlined />
                              : <SoundOutlined />
                          }
                          onClick={() => {
                            if (isPlaying && currentPlayingIndex === index) {
                              stopAudio();
                            } else {
                              playAudio(message.audioData!, message.audioFormat!, index);
                            }
                          }}
                          style={{ backgroundColor: '#059669' }}
                        >
                          {isPlaying && currentPlayingIndex === index ? 'Stop' : 'Play Audio'}
                        </Button>
                      </div>
                    )}

                    <div style={{ marginTop: '4px' }}>
                      <span
                        style={{
                          fontSize: '11px',
                          color: message.role === 'user' ? 'rgba(255,255,255,0.7)' : '#8c8c8c',
                        }}
                      >
                        {message.timestamp.toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Execution Log Panel */}
        {showExecutionLog && (
          <div
            style={{
              backgroundColor: '#f0f5ff',
              borderTop: '3px solid #1890ff',
              padding: '12px',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '12px',
                padding: '8px 12px',
                backgroundColor: '#1890ff',
                borderRadius: '6px',
                color: 'white',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CodeOutlined style={{ fontSize: '16px' }} />
                <span style={{ fontWeight: 'bold', fontSize: '14px' }}>Execution Log</span>
                {lastExecutionError && (
                  <Tag color="error" style={{ marginLeft: '8px' }}>Error</Tag>
                )}
                {!lastExecutionError && lastExecutionTrace.length > 0 && (
                  <Tag color="success" style={{ marginLeft: '8px' }}>{lastExecutionTrace.length} nodes executed</Tag>
                )}
              </div>
            </div>
            <div style={{ backgroundColor: 'white', borderRadius: '8px', padding: '12px' }}>
                {/* Error Alert */}
                {lastExecutionError && (
                  <Alert
                    message="Execution Error"
                    description={lastExecutionError}
                    type="error"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                )}

                {/* Node Execution Trace */}
                {lastExecutionTrace.length > 0 && (
                  <div className="space-y-3" style={{ maxHeight: '300px', overflow: 'auto' }}>
                    {lastExecutionTrace.map((entry, index) => {
                      const statusDisplay = getStatusDisplay(entry.status);
                      return (
                        <Card
                          key={`${entry.node_id}-${index}`}
                          size="small"
                          style={{
                            borderLeft: `4px solid ${getNodeTypeColor(entry.node_type)}`,
                            backgroundColor: entry.status === 'error' ? '#fff2f0' : 'white',
                          }}
                        >
                          <div className="flex justify-between items-start mb-2">
                            <div className="flex items-center gap-2">
                              <Tag color={getNodeTypeColor(entry.node_type)}>
                                {entry.node_type}
                              </Tag>
                              <Text strong>{entry.node_label || entry.node_id}</Text>
                            </div>
                            <div className="flex items-center gap-2">
                              {entry.duration_ms !== undefined && (
                                <Tag icon={<ClockCircleOutlined />}>
                                  {entry.duration_ms}ms
                                </Tag>
                              )}
                              <Tag
                                icon={statusDisplay.icon}
                                color={entry.status === 'error' ? 'error' : entry.status === 'success' ? 'success' : 'warning'}
                              >
                                {statusDisplay.text}
                              </Tag>
                            </div>
                          </div>

                          {/* Error message for this node */}
                          {entry.error && (
                            <Alert
                              message={entry.error}
                              type="error"
                              showIcon
                              style={{ marginBottom: 8 }}
                            />
                          )}

                          {/* Input/Output Data */}
                          <Collapse ghost size="small">
                            <Panel header={<Text type="secondary">Input Data</Text>} key="input">
                              {renderNodeData(entry.input_data)}
                            </Panel>
                            <Panel header={<Text type="secondary">Output Data</Text>} key="output">
                              {renderNodeData(entry.output_data)}
                            </Panel>
                          </Collapse>
                        </Card>
                      );
                    })}
                  </div>
                )}

                {lastExecutionTrace.length === 0 && !lastExecutionError && (
                  <div>
                    <Text type="secondary">No execution trace available yet.</Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: 11 }}>
                      Run a test to see the execution details here.
                    </Text>
                  </div>
                )}
            </div>
          </div>
        )}

        <Divider style={{ margin: 0 }} />

        {/* Input Area */}
        <div className="p-4 bg-white">
          <div className="mb-3 flex items-center gap-2">
            <Text strong>Input Mode:</Text>
            <Select
              value={inputMode}
              onChange={(value) => {
                setInputMode(value);
                setAudioBlob(null);
                if (audioUrl) {
                  URL.revokeObjectURL(audioUrl);
                  setAudioUrl(null);
                }
              }}
              style={{ width: 150 }}
              options={[
                { label: 'Chat', value: 'chat' },
                { label: 'JSON', value: 'json' },
                { label: 'Form', value: 'form' },
                { label: '🎤 Audio', value: 'audio' },
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
            ) : inputMode === 'audio' ? (
              <div className="flex-1 border rounded-lg p-4 bg-gray-50">
                <div className="flex items-center gap-4">
                  {/* Record Button */}
                  <Button
                    type={isRecording ? 'primary' : 'default'}
                    danger={isRecording}
                    icon={<AudioOutlined />}
                    onClick={isRecording ? stopRecording : startRecording}
                    size="large"
                  >
                    {isRecording ? `Stop (${formatTime(recordingTime)})` : 'Record'}
                  </Button>

                  <Text type="secondary">or</Text>

                  {/* Upload Button */}
                  <Upload
                    accept="audio/*"
                    showUploadList={false}
                    beforeUpload={handleAudioUpload}
                  >
                    <Button icon={<UploadOutlined />}>Upload Audio</Button>
                  </Upload>
                </div>

                {/* Recording indicator */}
                {isRecording && (
                  <div className="mt-3">
                    <Progress
                      percent={100}
                      status="active"
                      strokeColor="#ff4d4f"
                      showInfo={false}
                    />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      Recording... {formatTime(recordingTime)}
                    </Text>
                  </div>
                )}

                {/* Audio preview */}
                {audioUrl && !isRecording && (
                  <div className="mt-3">
                    <audio controls src={audioUrl} style={{ width: '100%' }} />
                    <Button
                      type="link"
                      danger
                      size="small"
                      onClick={() => {
                        setAudioBlob(null);
                        URL.revokeObjectURL(audioUrl);
                        setAudioUrl(null);
                      }}
                    >
                      Remove
                    </Button>
                  </div>
                )}
              </div>
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
              disabled={
                isLoading ||
                isRecording ||
                (inputMode === 'chat' ? !input.trim() :
                 inputMode === 'audio' ? !audioBlob :
                 !jsonInput.trim())
              }
              size="large"
            >
              Send
            </Button>
          </div>

          <Text type="secondary" style={{ fontSize: 11, marginTop: 8, display: 'block' }}>
            {inputMode === 'chat' && 'Conversational text input'}
            {inputMode === 'json' && 'Structured JSON data with schema validation'}
            {inputMode === 'form' && 'Form data as JSON object'}
            {inputMode === 'audio' && 'Record from microphone or upload audio file for voice input'}
          </Text>
        </div>
      </Card>
    </div>
  );
};
