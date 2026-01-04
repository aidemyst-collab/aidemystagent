import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { SendOutlined } from '@ant-design/icons';
import { Card } from 'antd';
import type { NodeProps } from '@xyflow/react';

export const WhatsAppOutputNode = memo(({ data, selected }: NodeProps) => {
  const config = (data as any).config || {};
  const responseType = config.responseType || 'text';
  const templateName = config.templateName || '';
  const buttons = config.buttons || [];
  const mediaType = config.mediaType || 'image';
  const color = '#128C7E'; // WhatsApp teal

  // Response type labels and icons
  const typeConfig: Record<string, { label: string; icon: string }> = {
    'text': { label: 'Text Message', icon: '💬' },
    'template': { label: 'Template', icon: '📋' },
    'media': { label: 'Media', icon: '🖼️' },
    'interactive': { label: 'Interactive', icon: '🔘' },
  };

  const currentType = typeConfig[responseType] || typeConfig['text'];

  // Media type labels
  const mediaLabels: Record<string, string> = {
    'image': 'Image',
    'video': 'Video',
    'audio': 'Audio',
    'document': 'Document',
  };

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
          minWidth: 200,
          backgroundColor: selected ? `${color}10` : 'white',
        }}
      >
        <div className="flex items-center gap-2">
          <div style={{ color, fontSize: 24 }}>
            <SendOutlined />
          </div>
          <div>
            <div className="font-semibold">
              {(data as any).label || 'WhatsApp Output'}
            </div>
            <div className="text-xs text-gray-500">
              {currentType.icon} {currentType.label}
            </div>
          </div>
        </div>

        <div style={{ fontSize: 10, color: '#666', marginTop: 8, maxWidth: 180 }}>
          {/* Response Type */}
          <div style={{ marginBottom: 2 }}>
            <span style={{ color }}>Type:</span> {currentType.label}
          </div>

          {/* Template specific */}
          {responseType === 'template' && (
            <>
              {templateName ? (
                <div style={{ marginBottom: 2 }}>
                  <span style={{ color }}>Template:</span> {templateName}
                </div>
              ) : (
                <div style={{ color: '#ff9800', marginBottom: 2 }}>
                  ⚠️ No template selected
                </div>
              )}
              {config.templateLanguage && (
                <div style={{ marginBottom: 2 }}>
                  <span style={{ color }}>Lang:</span> {config.templateLanguage}
                </div>
              )}
            </>
          )}

          {/* Media specific */}
          {responseType === 'media' && (
            <div style={{ marginBottom: 2 }}>
              <span style={{ color }}>Media:</span> {mediaLabels[mediaType] || mediaType}
            </div>
          )}

          {/* Interactive specific */}
          {responseType === 'interactive' && (
            <>
              <div style={{ marginBottom: 2 }}>
                <span style={{ color }}>Style:</span>{' '}
                {config.interactiveType === 'list' ? 'List Menu' : 'Buttons'}
              </div>
              {config.interactiveType !== 'list' && buttons.length > 0 ? (
                <div style={{ marginTop: 4 }}>
                  {buttons.slice(0, 3).map((btn: any, idx: number) => (
                    <span
                      key={idx}
                      style={{
                        display: 'inline-block',
                        backgroundColor: `${color}20`,
                        color: color,
                        padding: '1px 6px',
                        borderRadius: 4,
                        marginRight: 4,
                        marginBottom: 2,
                        fontSize: 9,
                      }}
                    >
                      {btn.title || `Button ${idx + 1}`}
                    </span>
                  ))}
                </div>
              ) : config.interactiveType !== 'list' ? (
                <div style={{ color: '#ff9800', marginTop: 2 }}>
                  ⚠️ No buttons configured
                </div>
              ) : null}
              {config.interactiveType === 'list' && (
                <div style={{ marginTop: 2 }}>
                  <span style={{ color }}>Sections:</span>{' '}
                  {config.sections?.length || 0}
                </div>
              )}
            </>
          )}

          {/* Fallback message preview */}
          {config.fallbackMessage && (
            <div
              style={{
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                fontStyle: 'italic',
                marginTop: 4,
                color: '#888',
              }}
              title={config.fallbackMessage}
            >
              Fallback: "{config.fallbackMessage.substring(0, 20)}..."
            </div>
          )}

          {/* Status indicator */}
          {responseType === 'text' && (
            <div style={{ color: '#22c55e', marginTop: 4 }}>✓ Ready to send</div>
          )}
          {responseType === 'template' && templateName && (
            <div style={{ color: '#22c55e', marginTop: 4 }}>✓ Template ready</div>
          )}
          {responseType === 'interactive' && buttons.length > 0 && (
            <div style={{ color: '#22c55e', marginTop: 4 }}>✓ {buttons.length} button(s)</div>
          )}
        </div>
      </Card>
    </>
  );
});

WhatsAppOutputNode.displayName = 'WhatsAppOutputNode';

export default WhatsAppOutputNode;
