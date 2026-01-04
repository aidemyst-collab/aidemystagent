import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { PhoneOutlined } from '@ant-design/icons';
import { Card } from 'antd';
import type { NodeProps } from '@xyflow/react';

export const VoiceInputNode = memo(({ data, selected }: NodeProps) => {
  const config = (data as any).config || {};
  const provider = config.provider || 'twilio';
  const language = config.language || 'en-US';
  const greeting = config.greeting || '';
  const color = '#10B981';

  // Format provider for display
  const providerLabels: Record<string, string> = {
    'twilio': 'Twilio',
    'etisalat': 'Etisalat CPaaS',
  };
  const providerLabel = providerLabels[provider] || provider;

  // Format language
  const languageLabels: Record<string, string> = {
    'en-US': 'English (US)',
    'en-GB': 'English (UK)',
    'ar-AE': 'Arabic (UAE)',
    'ar-SA': 'Arabic (SA)',
    'hi-IN': 'Hindi',
    'fr-FR': 'French',
    'de-DE': 'German',
    'es-ES': 'Spanish',
  };
  const languageLabel = languageLabels[language] || language;

  // Truncate greeting for display
  const truncatedGreeting = greeting.length > 30
    ? greeting.substring(0, 30) + '...'
    : greeting;

  return (
    <>
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
            <PhoneOutlined />
          </div>
          <div>
            <div className="font-semibold">
              {(data as any).label || 'Voice Input'}
            </div>
            <div className="text-xs text-gray-500">
              {providerLabel}
            </div>
          </div>
        </div>

        <div style={{ fontSize: 10, color: '#666', marginTop: 8, maxWidth: 160 }}>
          <div style={{ marginBottom: 2 }}>
            <span style={{ color }}>Language:</span> {languageLabel}
          </div>
          {config.maxDuration && (
            <div style={{ marginBottom: 2 }}>
              <span style={{ color }}>Max:</span> {config.maxDuration}s
            </div>
          )}
          {truncatedGreeting ? (
            <div
              style={{
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                fontStyle: 'italic',
              }}
              title={greeting}
            >
              "{truncatedGreeting}"
            </div>
          ) : (
            <div style={{ color: '#ff9800' }}>⚠️ No greeting set</div>
          )}
          {!config.credentialId && (
            <div style={{ color: '#ff9800', marginTop: 2 }}>⚠️ No credential</div>
          )}
          {config.credentialId && (
            <div style={{ color: '#22c55e', marginTop: 2 }}>✓ Configured</div>
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

VoiceInputNode.displayName = 'VoiceInputNode';

export default VoiceInputNode;
