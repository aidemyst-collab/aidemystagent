import { RobotOutlined } from '@ant-design/icons';
import { Handle, Position } from '@xyflow/react';
import { Card } from 'antd';
import type { NodeProps } from '@xyflow/react';

export const LLMAgentNode = (props: NodeProps) => {
  const { data, selected } = props;
  const color = '#1890ff';

  return (
    <>
      {/* Left handle - INPUT from main flow */}
      <Handle
        type="target"
        position={Position.Left}
        id="input"
        style={{
          background: '#52c41a',
          width: 14,
          height: 14,
          left: -7,
          border: '2px solid white',
          cursor: 'crosshair',
        }}
      />

      {/* Main LLM Agent Card */}
      <Card
        size="small"
        style={{
          border: selected ? `3px solid ${color}` : `2px solid ${color}`,
          borderRadius: 8,
          minWidth: 250,
          minHeight: 100,
          backgroundColor: selected ? `${color}10` : 'white',
          position: 'relative',
        }}
      >
        <div className="flex items-center gap-3">
          <div style={{ color, fontSize: 28 }}>
            <RobotOutlined />
          </div>
          <div>
            <div className="font-semibold text-base">
              {(data as any).label || 'LLM Agent'}
            </div>
            <div className="text-xs text-gray-500">
              AI Language Model
            </div>
          </div>
        </div>

        {/* Bottom handle labels */}
        <div
          style={{
            position: 'absolute',
            bottom: -2,
            left: 0,
            right: 0,
            display: 'flex',
            justifyContent: 'space-around',
            fontSize: 9,
            color: '#999',
            pointerEvents: 'none',
          }}
        >
          <span>mem</span>
          <span>tools</span>
          <span>rag</span>
        </div>
      </Card>

      {/* Right handle - OUTPUT to main flow */}
      <Handle
        type="source"
        position={Position.Right}
        id="output"
        style={{
          background: '#f5222d',
          width: 14,
          height: 14,
          right: -7,
          border: '2px solid white',
          cursor: 'crosshair',
        }}
      />

      {/* Bottom handles - connections TO auxiliary nodes */}
      <Handle
        type="source"
        position={Position.Bottom}
        id="memory"
        style={{
          background: '#fa8c16',
          width: 12,
          height: 12,
          bottom: -6,
          left: '20%',
          border: '2px solid white',
          cursor: 'crosshair',
        }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="tools"
        style={{
          background: '#13c2c2',
          width: 12,
          height: 12,
          bottom: -6,
          left: '50%',
          transform: 'translateX(-50%)',
          border: '2px solid white',
          cursor: 'crosshair',
        }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        id="rag"
        style={{
          background: '#722ed1',
          width: 12,
          height: 12,
          bottom: -6,
          left: '80%',
          border: '2px solid white',
          cursor: 'crosshair',
        }}
      />
    </>
  );
};
