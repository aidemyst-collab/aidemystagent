export { InputNode } from './InputNode';
export { MemoryNode } from './MemoryNode';
export { LLMAgentNode } from './LLMAgentNode';
export { RAGRetrieverNode } from './RAGRetrieverNode';
export { DecisionNode } from './DecisionNode';
export { ToolNode } from './ToolNode';
export { OutputNode } from './OutputNode';
export { SubgraphNode } from './SubgraphNode';
export { ExecuteWorkflowNode } from './ExecuteWorkflowNode';
export { AuxiliaryNode } from './AuxiliaryNode';
export { FileReaderNode } from './FileReaderNode';
export { StructuredOutputParserNode } from './StructuredOutputParserNode';
export { AudioToTextNode } from './AudioToTextNode';
export { TextToAudioNode } from './TextToAudioNode';
export { CodeNode } from './CodeNode';
export { VoiceInputNode } from './VoiceInputNode';
export { VoiceOutputNode } from './VoiceOutputNode';
export { WhatsAppInputNode } from './WhatsAppInputNode';
export { WhatsAppOutputNode } from './WhatsAppOutputNode';

export const nodeTypes = {
  INPUT: 'InputNode',
  MEMORY: 'MemoryNode',
  LLM_AGENT: 'LLMAgentNode',
  RAG_RETRIEVER: 'RAGRetrieverNode',
  DECISION: 'DecisionNode',
  TOOL: 'ToolNode',
  OUTPUT: 'OutputNode',
  SUBGRAPH: 'SubgraphNode',
  EXECUTE_WORKFLOW: 'ExecuteWorkflowNode',
  FILE_READER: 'FileReaderNode',
  STRUCTURED_OUTPUT_PARSER: 'StructuredOutputParserNode',
  AUDIO_TO_TEXT: 'AudioToTextNode',
  TEXT_TO_AUDIO: 'TextToAudioNode',
  CODE: 'CodeNode',
  VOICE_INPUT: 'VoiceInputNode',
  VOICE_OUTPUT: 'VoiceOutputNode',
  WHATSAPP_INPUT: 'WhatsAppInputNode',
  WHATSAPP_OUTPUT: 'WhatsAppOutputNode',
};
