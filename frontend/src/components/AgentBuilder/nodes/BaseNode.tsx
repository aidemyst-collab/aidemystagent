import { Handle, Position } from 'reactflow';
import { Card } from 'antd';
import { ReactNode } from 'react';

interface BaseNodeProps {
  data: {
    label: string;
    [key: string]: any;
  };
  selected?: boolean;
  icon: ReactNode;
  color: string;
  hasInput?: boolean;
  hasOutput?: boolean;
}

export const BaseNode = ({
  data,
  selected,
  icon,
  color,
  hasInput = true,
  hasOutput = true,
}: BaseNodeProps) => {
  return (
    <>
      {hasInput && (
        <Handle
          type="target"
          position={Position.Top}
          style={{ background: color }}
        />
      )}
      <Card
        size="small"
        style={{
          border: selected ? `2px solid ${color}` : `1px solid ${color}`,
          borderRadius: 8,
          minWidth: 180,
          backgroundColor: selected ? `${color}10` : 'white',
        }}
      >
        <div className="flex items-center gap-2">
          <div style={{ color }}>{icon}</div>
          <div className="font-medium">{data.label}</div>
        </div>
      </Card>
      {hasOutput && (
        <Handle
          type="source"
          position={Position.Bottom}
          style={{ background: color }}
        />
      )}
    </>
  );
};
