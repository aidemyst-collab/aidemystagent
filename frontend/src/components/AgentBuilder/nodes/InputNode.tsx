import { LoginOutlined } from '@ant-design/icons';
import { BaseNode } from './BaseNode';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';

export const InputNode = (props: NodeProps) => {
  return (
    <BaseNode
      {...props}
      icon={<LoginOutlined />}
      color="#52c41a"
      hasInput={false}
      minWidth={120}
    />
  );
};
