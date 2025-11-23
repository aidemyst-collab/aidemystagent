import { DatabaseOutlined } from '@ant-design/icons';
import { BaseNode } from './BaseNode';
import { NodeProps } from '@xyflow/react';

export const RAGRetrieverNode = (props: NodeProps) => {
  return (
    <BaseNode
      {...props}
      icon={<DatabaseOutlined />}
      color="#722ed1"
    />
  );
};
