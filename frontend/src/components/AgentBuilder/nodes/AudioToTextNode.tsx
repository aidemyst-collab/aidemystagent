import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { AudioOutlined } from '@ant-design/icons';
import { Card } from 'antd';
import type { NodeProps } from '@xyflow/react';

export const AudioToTextNode = memo(({ data, selected }: NodeProps) => {
  const config = (data as any).config || {};
  const provider = config.provider || 'openai_whisper';
  const audioSource = config.audioSource || 'url';
  const color = '#9333EA';

  // Format provider for display
  const providerLabels: Record<string, string> = {
    'openai_whisper': 'OpenAI Whisper',
    'deepgram': 'Deepgram',
    'assemblyai': 'AssemblyAI',
    'google_stt': 'Google STT',
  };
  const providerLabel = providerLabels[provider] || provider;

  // Format audio source
  const sourceLabels: Record<string, string> = {
    'url': 'Audio URL',
    'base64': 'Base64 Data',
    'twilio_stream': 'Twilio Stream',
  };
  const sourceLabel = sourceLabels[audioSource] || audioSource;

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
            <AudioOutlined />
          </div>
          <div>
            <div className="font-semibold">
              {(data as any).label || 'Audio to Text'}
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
          {config.language && (
            <div style={{ marginBottom: 2 }}>
              <span style={{ color }}>Language:</span> {config.language}
            </div>
          )}
          {audioSource === 'url' && config.audioUrl ? (
            <div
              style={{
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                fontFamily: 'monospace',
              }}
              title={config.audioUrl}
            >
              🔗 {config.audioUrl}
            </div>
          ) : audioSource === 'twilio_stream' ? (
            <div style={{ color: '#22c55e' }}>📞 Twilio mulaw 8kHz</div>
          ) : !config.credentialId ? (
            <div style={{ color: '#ff9800' }}>⚠️ No credential</div>
          ) : null}
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

AudioToTextNode.displayName = 'AudioToTextNode';
