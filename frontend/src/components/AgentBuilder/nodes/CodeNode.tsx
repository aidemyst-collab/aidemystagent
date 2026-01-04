import { CodeOutlined } from '@ant-design/icons';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';

export const CodeNode = ({ data, selected }: NodeProps) => {
  const color = '#F59E0B'; // Amber color for code

  return (
    <>
      {/* Top handle - RECEIVES connection FROM upstream node */}
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: color, width: 10, height: 10, top: -5 }}
      />

      {/* Rectangular node design for code */}
      <div
        style={{
          width: 120,
          minHeight: 70,
          borderRadius: 8,
          border: selected ? `3px solid ${color}` : `2px solid ${color}`,
          backgroundColor: selected ? `${color}15` : 'white',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 12,
          boxShadow: selected ? `0 0 10px ${color}40` : '0 2px 4px rgba(0,0,0,0.1)',
        }}
      >
        <div style={{ color, fontSize: 24, marginBottom: 4 }}>
          <CodeOutlined />
        </div>
        <div
          style={{
            fontSize: 12,
            fontWeight: 600,
            textAlign: 'center',
            color: '#333',
            lineHeight: 1.2,
          }}
        >
          {(data as any).label || 'Code'}
        </div>
        <div
          style={{
            fontSize: 10,
            color: '#666',
            marginTop: 2,
          }}
        >
          {(data as any).config?.language === 'python' ? 'Python' : 'JavaScript'}
        </div>
      </div>

      {/* Bottom handle - SENDS output to downstream node */}
      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: color, width: 10, height: 10, bottom: -5 }}
      />
    </>
  );
};
