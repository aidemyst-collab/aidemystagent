import type { Node, Edge } from '@xyflow/react';
import type { NodeField } from './nodeSchemas';

// Node Types
export type NodeType =
  | 'INPUT'
  | 'MEMORY'
  | 'LLM_AGENT'
  | 'RAG_RETRIEVER'
  | 'DECISION'
  | 'TOOL'
  | 'OUTPUT'
  | 'SUBGRAPH'
  | 'FILE_READER'
  | 'STRUCTURED_OUTPUT_PARSER'
  | 'AUDIO_TO_TEXT'
  | 'TEXT_TO_AUDIO'
  | 'CODE'
  | 'VOICE_INPUT'
  | 'VOICE_OUTPUT'
  | 'WHATSAPP_INPUT'
  | 'WHATSAPP_OUTPUT';

// Node-Specific Configuration Interfaces

export interface InputNodeConfig {
  mode?: 'chat' | 'json' | 'form' | 'audio'; // Input mode
  schema?: Record<string, any>; // Optional input validation schema
  customOutputFields?: NodeField[]; // Custom output fields defined by user

  // Audio mode configuration (receive & normalize only - NO transcription)
  audioConfig?: {
    // Source of audio input
    source: 'twilio' | 'microphone' | 'upload' | 'url';

    // Twilio-specific settings
    twilioConfig?: {
      format: 'mulaw' | 'pcm';
      sampleRate: number; // 8000 for Twilio
    };

    // URL source settings
    audioUrl?: string;

    // Output format after normalization
    outputFormat?: 'wav' | 'mp3' | 'webm'; // Normalized format for next node
  };
}

export interface MemoryNodeConfig {
  type?: 'buffer' | 'buffer-window' | 'summary' | 'vector' | 'entity';
  windowSize?: number;
  persistence?: {
    enabled: boolean;
    backend?: 'redis' | 'postgres' | 'mongodb';
    ttlDays?: number;
  };
}

export interface LLMAgentNodeConfig {
  credentialId?: string; // ID of the credential to use for this LLM node
  modelConfig: {
    model: string; // 'gpt-4', 'gpt-3.5-turbo', 'claude-3-opus', etc.
    temperature: number;
    maxTokens: number;
  };
  systemPrompt: string;
  tools: string[]; // Array of tool IDs available to this LLM
}

export interface RAGRetrieverNodeConfig {
  // RAG source selection
  ragSource: 'internal' | 'external';

  // External RAG (DemystRAG) configuration
  externalUrl?: string;
  externalApiKey?: string;

  // Internal RAG configuration
  endpoint?: string;
  authType?: 'api_key' | 'oauth2' | 'basic';
  credentialId?: string;
  embeddingProvider?: string;
  embeddingModel?: string;

  // Common settings
  collectionId?: number;
  searchMethod?: 'semantic' | 'hybrid' | 'keyword' | 'cosine' | 'l2';
  topK: number;
  scoreThreshold: number;
  includeMetadata?: boolean;
}

export interface DecisionNodeConfig {
  conditions: Array<{
    field: string;
    operator: '==' | '!=' | '>' | '<' | '>=' | '<=' | 'contains';
    value: any;
    targetNode: string;
  }>;
}

export interface ToolNodeConfig {
  toolId: string;
  parameters: Record<string, any>;
  customOutputFields?: NodeField[]; // Custom output fields defined by user
}

export interface OutputNodeConfig {
  format: 'json' | 'text' | 'markdown' | 'audio';
  template?: string;
  customOutputFields?: NodeField[]; // Custom output fields defined by user

  // Audio output configuration (receives audio from TEXT_TO_AUDIO node)
  audioConfig?: {
    // Target provider to send audio back to
    targetProvider: 'twilio' | 'browser' | 'api' | 'auto'; // 'auto' detects from INPUT source

    // Twilio-specific response settings
    twilioConfig?: {
      responseType: 'twiml_play' | 'twiml_say'; // play = custom audio, say = Twilio TTS
      playUrl?: string; // URL where audio is hosted (for twiml_play)
      sayVoice?: string; // Twilio voice (for twiml_say)
      sayLanguage?: string; // Language for Twilio TTS
    };

    // Browser/API response settings
    includeTranscript?: boolean; // Include text alongside audio
    autoPlay?: boolean; // Auto-play audio in playground

    // Audio source (from TEXT_TO_AUDIO node)
    audioSourceNodeId?: string; // Reference to TEXT_TO_AUDIO node
  };
}

export interface SubgraphNodeConfig {
  workflowId: string; // Reference to another workflow
}

export interface FileReaderNodeConfig {
  filePath: string;
  operation: 'read_text' | 'read_binary' | 'read_json' | 'read_csv' | 'read_lines' | 'get_metadata';
  encoding?: string;
  maxFileSizeMB?: number;
  errorHandling: 'fail' | 'continue' | 'default_value';
  defaultValue?: string;
  outputVarName?: string;
  // CSV Options
  csvDelimiter?: string;
  csvHasHeader?: boolean;
  csvSkipEmpty?: boolean;
  csvTrimFields?: boolean;
  // JSON Options
  validateSchema?: boolean;
  jsonSchema?: string;
  // Line Reading Options
  linesSkipEmpty?: boolean;
  linesTrim?: boolean;
  linesStart?: number;
  linesEnd?: number;
}

export interface AudioToTextNodeConfig {
  // Audio source configuration
  audioSource: 'previous_node' | 'url' | 'base64' | 'twilio_stream';

  // When audioSource is 'previous_node' - reference to INPUT node output
  sourceNodeId?: string; // e.g., 'input-1'
  sourceField?: string; // e.g., 'audio_data' (default)

  // When audioSource is 'url'
  audioUrl?: string;

  // When audioSource is 'base64'
  audioData?: string; // Base64 encoded audio

  // Audio format settings
  audioFormat?: 'wav' | 'mp3' | 'mulaw' | 'ogg' | 'webm' | 'flac';
  sampleRate?: number;
  twilioFormat?: boolean; // If true, treats as mulaw 8kHz

  // Transcription provider configuration
  provider: 'openai_whisper' | 'deepgram' | 'assemblyai' | 'google_stt';
  credentialId?: string;
  model?: string;
  language?: string;
}

export interface TextToAudioNodeConfig {
  // Text source configuration
  textSource: 'template' | 'last_message' | 'fixed';
  textTemplate?: string; // Template with {{node_id.field}} syntax
  fixedText?: string; // Fixed text to synthesize

  // TTS provider configuration
  provider: 'openai_tts' | 'elevenlabs' | 'google_tts' | 'amazon_polly';
  credentialId?: string;
  voice?: string;
  model?: string;

  // Output configuration
  outputFormat?: 'mp3' | 'wav' | 'ogg' | 'mulaw';
  speed?: number; // 0.5 to 2.0
  language?: string;
}

export interface CodeNodeConfig {
  // Language selection
  language: 'javascript' | 'python';

  // The code to execute
  code: string;

  // Input mapping - which node outputs to pass as input
  inputMapping?: {
    variableName: string;  // Variable name in the code
    sourceNodeId: string;  // Node to get data from
    sourceField?: string;  // Specific field from node output
  }[];

  // Output variable name (what to return from the code)
  outputVariable?: string;

  // Timeout in milliseconds
  timeout?: number;

  // Enable/disable sandboxing (security)
  sandboxed?: boolean;
}

export interface VoiceInputNodeConfig {
  // Voice provider selection
  provider: 'twilio' | 'etisalat';

  // Credential ID for the selected provider
  credentialId: string;

  // Greeting message to play when call connects
  greeting?: string;

  // Language for text-to-speech
  language?: string;

  // Recording settings
  maxDuration?: number; // seconds (default: 60)
  silenceTimeout?: number; // seconds (default: 3)
  playBeep?: boolean;
  trimSilence?: boolean;

  // Output audio format
  audioFormat?: 'wav' | 'mp3' | 'mulaw';
}

export interface VoiceOutputNodeConfig {
  // Field name containing audio data from previous node
  inputField?: string;

  // Audio format
  audioFormat?: 'wav' | 'mp3' | 'mulaw';

  // Action after playing audio
  afterResponse?: 'hangup' | 'continue' | 'transfer';

  // Phone number to transfer to (if afterResponse is 'transfer')
  transferTo?: string;

  // Fallback message if no audio available
  fallbackMessage?: string;

  // Voice for fallback TTS
  fallbackVoice?: string;

  // Number of times to loop audio
  loop?: number;
}

export interface WhatsAppInputNodeConfig {
  // Credential ID for Meta Cloud API
  credentialId?: string;

  // Webhook verify token (for Meta webhook verification)
  verifyToken?: string;

  // Accepted message types
  messageTypes?: ('text' | 'image' | 'video' | 'audio' | 'document' | 'location' | 'interactive')[];

  // Language for responses
  language?: string;

  // Welcome message for new conversations
  welcomeMessage?: string;

  // Error message when processing fails
  errorMessage?: string;

  // Session timeout in seconds (default: 24 hours)
  sessionTimeout?: number;

  // Mark messages as read automatically
  autoMarkRead?: boolean;
}

export interface WhatsAppOutputNodeConfig {
  // Response type
  responseType: 'text' | 'template' | 'media' | 'interactive';

  // Template message settings
  templateName?: string;
  templateLanguage?: string;
  templateVariables?: Array<{
    type: 'text' | 'image' | 'document' | 'video';
    value: string;
  }>;

  // Media message settings
  mediaType?: 'image' | 'video' | 'audio' | 'document';
  mediaUrl?: string;
  mediaCaption?: string;
  mediaFilename?: string;

  // Interactive message settings
  interactiveType?: 'button' | 'list';
  buttons?: Array<{
    id: string;
    title: string; // Max 20 chars
  }>;
  sections?: Array<{
    title: string;
    rows: Array<{
      id: string;
      title: string;
      description?: string;
    }>;
  }>;
  listButtonText?: string;

  // Header/Footer for interactive
  headerText?: string;
  footerText?: string;

  // Fallback message if sending fails
  fallbackMessage?: string;
}

// Union type for all node configs
export type NodeConfig =
  | InputNodeConfig
  | LLMAgentNodeConfig
  | RAGRetrieverNodeConfig
  | DecisionNodeConfig
  | ToolNodeConfig
  | OutputNodeConfig
  | SubgraphNodeConfig
  | FileReaderNodeConfig
  | AudioToTextNodeConfig
  | TextToAudioNodeConfig
  | CodeNodeConfig
  | VoiceInputNodeConfig
  | VoiceOutputNodeConfig
  | WhatsAppInputNodeConfig
  | WhatsAppOutputNodeConfig;

// Node Data Interface
export interface WorkflowNodeData {
  label: string;
  type: NodeType;
  config?: NodeConfig;
  [key: string]: unknown; // Index signature for ReactFlow compatibility
}

// Node and Edge Types for ReactFlow
export type WorkflowNode = Node<WorkflowNodeData>;
export type WorkflowEdge = Edge;

// Workflow Configuration
export interface WorkflowConfig {
  id?: string;
  name: string;
  description: string;
  executionSettings: {
    timeout: number; // milliseconds
    retryPolicy: {
      maxRetries: number;
      retryDelay: number; // milliseconds
    };
  };
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  status: 'draft' | 'deployed' | 'archived';
  version: number;
  createdAt?: string;
  updatedAt?: string;
  creatorId?: string;
  organizationId?: string;
}

// Complete Workflow Interface
export interface Workflow extends WorkflowConfig {
  id: string;
  createdAt: string;
  updatedAt: string;
  creatorId: string;
  organizationId: string;
}

// Helper type guards
export function isLLMAgentNode(node: WorkflowNode): node is WorkflowNode & { data: { config: LLMAgentNodeConfig } } {
  return node.data.type === 'LLM_AGENT';
}

export function isRAGRetrieverNode(node: WorkflowNode): node is WorkflowNode & { data: { config: RAGRetrieverNodeConfig } } {
  return node.data.type === 'RAG_RETRIEVER';
}

export function isDecisionNode(node: WorkflowNode): node is WorkflowNode & { data: { config: DecisionNodeConfig } } {
  return node.data.type === 'DECISION';
}

export function isToolNode(node: WorkflowNode): node is WorkflowNode & { data: { config: ToolNodeConfig } } {
  return node.data.type === 'TOOL';
}

export function isOutputNode(node: WorkflowNode): node is WorkflowNode & { data: { config: OutputNodeConfig } } {
  return node.data.type === 'OUTPUT';
}

export function isSubgraphNode(node: WorkflowNode): node is WorkflowNode & { data: { config: SubgraphNodeConfig } } {
  return node.data.type === 'SUBGRAPH';
}
