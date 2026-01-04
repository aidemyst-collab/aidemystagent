import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { MessageOutlined } from '@ant-design/icons';
import { Card } from 'antd';
import type { NodeProps } from '@xyflow/react';

export const WhatsAppInputNode = memo(({ data, selected }: NodeProps) => {
  const config = (data as any).config || {};
  const messageTypes = config.messageTypes || ['text'];
  const language = config.language || 'en';
  const welcomeMessage = config.welcomeMessage || '';
  const color = '#25D366'; // WhatsApp brand green

  // Format language for display
  const languageLabels: Record<string, string> = {
    'en': 'English',
    'en-US': 'English (US)',
    'en-GB': 'English (UK)',
    'ar': 'Arabic',
    'ar-AE': 'Arabic (UAE)',
    'ar-SA': 'Arabic (SA)',
    'hi': 'Hindi',
    'fr': 'French',
    'de': 'German',
    'es': 'Spanish',
    'pt': 'Portuguese',
    'zh': 'Chinese',
  };
  const languageLabel = languageLabels[language] || language;

  // Format message types for display
  const typeLabels: Record<string, string> = {
    'text': 'Text',
    'image': 'Image',
    'video': 'Video',
    'audio': 'Audio',
    'document': 'Doc',
    'location': 'Location',
    'interactive': 'Interactive',
  };

  const displayTypes = messageTypes.slice(0, 3).map((t: string) => typeLabels[t] || t);
  const remainingCount = messageTypes.length - 3;

  // Truncate welcome message for display
  const truncatedWelcome = welcomeMessage.length > 30
    ? welcomeMessage.substring(0, 30) + '...'
    : welcomeMessage;

  return (
    <>
      <Card
        size="small"
        style={{
          border: selected ? `3px solid ${color}` : `2px solid ${color}`,
          borderRadius: 8,
          minWidth: 200,
          backgroundColor: selected ? `${color}10` : 'white',
        }}
      >
        <div className="flex items-center gap-2">
          <div style={{ color, fontSize: 24 }}>
            <MessageOutlined />
          </div>
          <div>
            <div className="font-semibold">
              {(data as any).label || 'WhatsApp Input'}
            </div>
            <div className="text-xs text-gray-500">
              Meta Cloud API
            </div>
          </div>
        </div>

        <div style={{ fontSize: 10, color: '#666', marginTop: 8, maxWidth: 180 }}>
          {/* Language */}
          <div style={{ marginBottom: 2 }}>
            <span style={{ color }}>Language:</span> {languageLabel}
          </div>

          {/* Accepted Message Types */}
          <div style={{ marginBottom: 2 }}>
            <span style={{ color }}>Accept:</span>{' '}
            {displayTypes.join(', ')}
            {remainingCount > 0 && ` +${remainingCount}`}
          </div>

          {/* Welcome Message */}
          {truncatedWelcome ? (
            <div
              style={{
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                fontStyle: 'italic',
                marginTop: 4,
              }}
              title={welcomeMessage}
            >
              "{truncatedWelcome}"
            </div>
          ) : (
            <div style={{ color: '#888', fontStyle: 'italic', marginTop: 4 }}>
              No welcome message
            </div>
          )}

          {/* Verify Token Status */}
          {!config.verifyToken && (
            <div style={{ color: '#ff9800', marginTop: 4 }}>⚠️ No verify token</div>
          )}
          {config.verifyToken && (
            <div style={{ color: '#22c55e', marginTop: 2 }}>✓ Token set</div>
          )}

          {/* Credential Status */}
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

WhatsAppInputNode.displayName = 'WhatsAppInputNode';

export default WhatsAppInputNode;
