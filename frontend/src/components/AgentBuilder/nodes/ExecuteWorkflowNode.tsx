import { PlayCircleOutlined } from '@ant-design/icons';
import { Handle, Position } from '@xyflow/react';
import { Card, Tag, Typography } from 'antd';
import type { NodeProps } from '@xyflow/react';

const { Text } = Typography;

export const ExecuteWorkflowNode = ({ data, selected }: NodeProps) => {
  const color = '#8B5CF6'; // Purple color for workflow execution
  const config = data.config || {};

  const getModeLabel = (mode: string) => {
    switch (mode) {
      case 'sync':
        return 'Sync';
      case 'async':
        return 'Async';
      case 'async_callback':
        return 'Callback';
      default:
        return 'Sync';
    }
  };

  const inputCount = config.inputMapping?.length || 0;
  const outputCount = config.outputMapping?.length || 0;

  return (
    <>
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: color }}
      />
      <Card
        size="small"
        style={{
          border: selected ? `2px solid ${color}` : `1px solid ${color}`,
          borderRadius: 8,
          minWidth: 200,
          backgroundColor: selected ? `${color}10` : 'white',
        }}
      >
        <div className="flex items-center gap-2 mb-2">
          <div style={{ color }}>
            <PlayCircleOutlined style={{ fontSize: 18 }} />
          </div>
          <div className="font-medium">{data.label || 'Execute Workflow'}</div>
        </div>

        {config.workflowName && (
          <div
            style={{
              background: '#f5f5f5',
              borderRadius: 4,
              padding: '4px 8px',
              marginBottom: 8,
            }}
          >
            <Text style={{ fontSize: 12 }} ellipsis>
              {config.workflowName}
            </Text>
          </div>
        )}

        {!config.workflowId && (
          <div
            style={{
              background: '#fff7e6',
              borderRadius: 4,
              padding: '4px 8px',
              marginBottom: 8,
              border: '1px dashed #ffa940',
            }}
          >
            <Text type="warning" style={{ fontSize: 11 }}>
              No workflow selected
            </Text>
          </div>
        )}

        <div className="flex items-center gap-2 flex-wrap">
          <Tag color="purple" style={{ margin: 0, fontSize: 10 }}>
            {getModeLabel(config.executionMode || 'sync')}
          </Tag>
          {inputCount > 0 && (
            <Tag color="blue" style={{ margin: 0, fontSize: 10 }}>
              {inputCount} input{inputCount > 1 ? 's' : ''}
            </Tag>
          )}
          {outputCount > 0 && (
            <Tag color="green" style={{ margin: 0, fontSize: 10 }}>
              {outputCount} output{outputCount > 1 ? 's' : ''}
            </Tag>
          )}
        </div>
      </Card>
      <Handle
        type="source"
        position={Position.Bottom}
        style={{ background: color }}
      />
    </>
  );
};
