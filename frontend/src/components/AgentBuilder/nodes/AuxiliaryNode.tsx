import { Handle, Position } from '@xyflow/react';
import { ReactNode } from 'react';
import type { NodeProps } from '@xyflow/react';

interface AuxiliaryNodeProps extends Omit<NodeProps, 'type'> {
  icon: ReactNode;
  color: string;
}

export const AuxiliaryNode = ({
  data,
  selected,
  icon,
  color,
}: AuxiliaryNodeProps) => {
  return (
    <>
      {/* Top handle - RECEIVES connection FROM LLM agent above */}
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: color, width: 10, height: 10, top: -5 }}
      />

      {/* Circular node design */}
      <div
        style={{
          width: 80,
          height: 80,
          borderRadius: '50%',
          border: selected ? `3px solid ${color}` : `2px dashed ${color}`,
          backgroundColor: selected ? `${color}20` : 'white',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 8,
          boxShadow: selected ? `0 0 10px ${color}40` : '0 2px 4px rgba(0,0,0,0.1)',
        }}
      >
        <div style={{ color, fontSize: 24, marginBottom: 4 }}>
          {icon}
        </div>
        <div
          style={{
            fontSize: 11,
            fontWeight: 500,
            textAlign: 'center',
            color: '#333',
            lineHeight: 1.2,
          }}
        >
          {(data as any).label || 'Node'}
        </div>
      </div>
    </>
  );
};
