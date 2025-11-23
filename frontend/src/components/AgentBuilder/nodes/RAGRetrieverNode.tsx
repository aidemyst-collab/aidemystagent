import { DatabaseOutlined } from '@ant-design/icons';
import { BaseNode } from './BaseNode';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';

export const RAGRetrieverNode = (props: NodeProps) => {
  return (
    <BaseNode
      {...props}
      icon={<DatabaseOutlined />}
      color="#722ed1"
    />
  );
};
