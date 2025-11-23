import { BranchesOutlined } from '@ant-design/icons';
import { BaseNode } from './BaseNode';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';

export const DecisionNode = (props: NodeProps) => {
  return (
    <BaseNode
      {...props}
      icon={<BranchesOutlined />}
      color="#fa8c16"
    />
  );
};
