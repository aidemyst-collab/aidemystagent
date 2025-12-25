import { ToolOutlined } from '@ant-design/icons';
import { AuxiliaryNode } from './AuxiliaryNode';
import type { NodeProps } from '@xyflow/react';

export const ToolNode = (props: NodeProps) => {
  return (
    <AuxiliaryNode
      {...props}
      icon={<ToolOutlined />}
      color="#13c2c2"
    />
  );
};
