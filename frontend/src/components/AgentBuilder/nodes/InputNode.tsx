import { LoginOutlined } from '@ant-design/icons';
import { BaseNode } from './BaseNode';
import { NodeProps } from '@xyflow/react';

export const InputNode = (props: NodeProps) => {
  return (
    <BaseNode
      {...props}
      icon={<LoginOutlined />}
      color="#52c41a"
      hasInput={false}
    />
  );
};
