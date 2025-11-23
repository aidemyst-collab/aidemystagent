import { RobotOutlined } from '@ant-design/icons';
import { BaseNode } from './BaseNode';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';

export const LLMAgentNode = (props: NodeProps) => {
  return (
    <BaseNode
      {...props}
      icon={<RobotOutlined />}
      color="#1890ff"
    />
  );
};
