import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { SoundOutlined } from '@ant-design/icons';
import { Card } from 'antd';
import type { NodeProps } from '@xyflow/react';

export const VoiceOutputNode = memo(({ data, selected }: NodeProps) => {
  const config = (data as any).config || {};
  const afterResponse = config.afterResponse || 'hangup';
  const audioFormat = config.audioFormat || 'mp3';
  const transferTo = config.transferTo || '';
  const loop = config.loop || 1;
  const color = '#3B82F6';

  // Format action for display
  const actionLabels: Record<string, string> = {
    'hangup': 'Hang Up',
    'continue': 'Continue',
    'transfer': 'Transfer',
  };
  const actionLabel = actionLabels[afterResponse] || afterResponse;

  // Format audio format
  const formatLabels: Record<string, string> = {
    'mp3': 'MP3',
    'wav': 'WAV',
    'mulaw': 'Mulaw',
  };
  const formatLabel = formatLabels[audioFormat] || audioFormat;

  // Action icon
  const actionIcons: Record<string, string> = {
    'hangup': '📵',
    'continue': '🔄',
    'transfer': '📲',
  };
  const actionIcon = actionIcons[afterResponse] || '📞';

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
              {(data as any).label || 'Voice Output'}
            </div>
            <div className="text-xs text-gray-500">
              {actionIcon} {actionLabel}
            </div>
          </div>
        </div>

        <div style={{ fontSize: 10, color: '#666', marginTop: 8, maxWidth: 160 }}>
          <div style={{ marginBottom: 2 }}>
            <span style={{ color }}>Format:</span> {formatLabel}
          </div>
          {loop > 1 && (
            <div style={{ marginBottom: 2 }}>
              <span style={{ color }}>Loop:</span> {loop}x
            </div>
          )}
          {afterResponse === 'transfer' && (
            <div style={{ marginBottom: 2 }}>
              {transferTo ? (
                <span>
                  <span style={{ color }}>To:</span> {transferTo}
                </span>
              ) : (
                <span style={{ color: '#ff9800' }}>⚠️ No transfer #</span>
              )}
            </div>
          )}
          {afterResponse === 'continue' && (
            <div style={{ color: '#22c55e' }}>🔄 Multi-turn enabled</div>
          )}
          {config.fallbackMessage ? (
            <div
              style={{
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                fontStyle: 'italic',
                marginTop: 2,
              }}
              title={config.fallbackMessage}
            >
              Fallback: "{config.fallbackMessage.substring(0, 20)}..."
            </div>
          ) : null}
        </div>
      </Card>
    </>
  );
});

VoiceOutputNode.displayName = 'VoiceOutputNode';

export default VoiceOutputNode;
