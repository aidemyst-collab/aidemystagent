import { ToolOutlined } from '@ant-design/icons';
import { BaseNode } from './BaseNode';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';

export const ToolNode = (props: NodeProps) => {
  return (
    <BaseNode
      {...props}
      icon={<ToolOutlined />}
      color="#13c2c2"
    />
  );
};
