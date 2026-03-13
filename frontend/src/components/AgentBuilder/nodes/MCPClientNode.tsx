import { ApiOutlined } from '@ant-design/icons';
import { AuxiliaryNode } from './AuxiliaryNode';
import type { NodeProps } from '@xyflow/react';

export const MCPClientNode = (props: NodeProps) => {
  return (
    <AuxiliaryNode
      {...props}
      icon={<ApiOutlined />}
      color="#eb2f96"
    />
  );
};
