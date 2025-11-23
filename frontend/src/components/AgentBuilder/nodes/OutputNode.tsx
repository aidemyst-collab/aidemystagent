import { ExportOutlined } from '@ant-design/icons';
import { BaseNode } from './BaseNode';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';

export const OutputNode = (props: NodeProps) => {
  return (
    <BaseNode
      {...props}
      icon={<ExportOutlined />}
      color="#f5222d"
      hasOutput={false}
    />
  );
};
