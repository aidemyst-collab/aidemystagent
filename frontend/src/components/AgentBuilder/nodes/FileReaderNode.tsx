import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { FileTextOutlined } from '@ant-design/icons';
import { BaseNode } from './BaseNode';
import type { NodeProps } from '@xyflow/react';

export const FileReaderNode = memo(({ data, selected }: NodeProps) => {
  const config = data.config || {};
  const operation = config.operation || 'read_text';
  const filePath = config.filePath || '';

  // Format operation for display
  const operationLabel = operation
    .replace('_', ' ')
    .split(' ')
    .map((word: string) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');

  return (
    <BaseNode
      icon={<FileTextOutlined style={{ fontSize: 24 }} />}
      title={data.label || 'File Reader'}
      subtitle={operationLabel}
      selected={selected}
      color="#3B82F6"
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{ background: '#3B82F6' }}
      />
      <div style={{ fontSize: 10, color: '#666', marginTop: 4, maxWidth: 150 }}>
        {filePath ? (
          <div
            style={{
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              fontFamily: 'monospace',
            }}
            title={filePath}
          >
            📁 {filePath}
          </div>
        ) : (
          <div style={{ color: '#ff9800' }}>⚠️ No file path</div>
        )}
      </div>
      <Handle
        type="source"
        position={Position.Right}
        style={{ background: '#3B82F6' }}
      />
    </BaseNode>
  );
});

FileReaderNode.displayName = 'FileReaderNode';
