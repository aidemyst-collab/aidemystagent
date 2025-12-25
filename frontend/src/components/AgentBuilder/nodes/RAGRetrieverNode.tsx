import { DatabaseOutlined } from '@ant-design/icons';
import { AuxiliaryNode } from './AuxiliaryNode';
import type { NodeProps } from '@xyflow/react';

export const RAGRetrieverNode = (props: NodeProps) => {
  return (
    <AuxiliaryNode
      {...props}
      icon={<DatabaseOutlined />}
      color="#722ed1"
    />
  );
};
