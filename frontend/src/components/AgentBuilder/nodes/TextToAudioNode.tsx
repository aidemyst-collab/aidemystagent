import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { SoundOutlined } from '@ant-design/icons';
import { Card } from 'antd';
import type { NodeProps } from '@xyflow/react';

export const TextToAudioNode = memo(({ data, selected }: NodeProps) => {
  const config = (data as any).config || {};
  const provider = config.provider || 'openai_tts';
  const textSource = config.textSource || 'last_message';
  const voice = config.voice;
  const color = '#059669'; // Emerald green

  // Format provider for display
  const providerLabels: Record<string, string> = {
    'openai_tts': 'OpenAI TTS',
    'elevenlabs': 'ElevenLabs',
    'google_tts': 'Google TTS',
    'amazon_polly': 'Amazon Polly',
  };
  const providerLabel = providerLabels[provider] || provider;

  // Format text source
  const sourceLabels: Record<string, string> = {
    'last_message': 'Last Message',
    'template': 'Template',
    'fixed': 'Fixed Text',
  };
  const sourceLabel = sourceLabels[textSource] || textSource;

  return (
    <>
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: color,
          width: 12,
          height: 12,
          left: -6,
          border: '2px solid white',
        }}
      />

      <Card
        size="small"
        style={{
          border: selected ? `3px solid ${color}` : `2px solid ${color}`,
          borderRadius: 8,
          minWidth: 180,
          backgroundColor: selected ? `${color}10` : 'white',
        }}
      >
        <div className="flex items-center gap-2">
          <div style={{ color, fontSize: 24 }}>
            <SoundOutlined />
          </div>
          <div>
            <div className="font-semibold">
              {(data as any).label || 'Text to Audio'}
            </div>
            <div className="text-xs text-gray-500">
              {providerLabel}
            </div>
          </div>
        </div>

        <div style={{ fontSize: 10, color: '#666', marginTop: 8, maxWidth: 150 }}>
          <div style={{ marginBottom: 2 }}>
            <span style={{ color }}>Source:</span> {sourceLabel}
          </div>
          {voice && (
            <div style={{ marginBottom: 2 }}>
              <span style={{ color }}>Voice:</span> {voice}
            </div>
          )}
          {config.outputFormat && (
            <div style={{ marginBottom: 2 }}>
              <span style={{ color }}>Format:</span> {config.outputFormat.toUpperCase()}
            </div>
          )}
          {textSource === 'template' && config.textTemplate ? (
            <div
              style={{
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                fontFamily: 'monospace',
                fontSize: 9,
              }}
              title={config.textTemplate}
            >
              📝 {config.textTemplate}
            </div>
          ) : !config.credentialId ? (
            <div style={{ color: '#ff9800' }}>⚠️ No credential</div>
          ) : (
            <div style={{ color: '#22c55e' }}>🔊 Ready</div>
          )}
        </div>
      </Card>

      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: color,
          width: 12,
          height: 12,
          right: -6,
          border: '2px solid white',
        }}
      />
    </>
  );
});

TextToAudioNode.displayName = 'TextToAudioNode';
