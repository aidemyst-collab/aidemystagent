import { RobotOutlined } from '@ant-design/icons';
import { BaseNode } from './BaseNode';
import { NodeProps } from '@xyflow/react';

export const LLMAgentNode = (props: NodeProps) => {
  return (
    <BaseNode
      {...props}
      icon={<RobotOutlined />}
      color="#1890ff"
    />
  );
};
