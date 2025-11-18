import { ToolOutlined } from '@ant-design/icons';
import { BaseNode } from './BaseNode';
import { NodeProps } from 'reactflow';

export const ToolNode = (props: NodeProps) => {
  return (
    <BaseNode
      {...props}
      icon={<ToolOutlined />}
      color="#13c2c2"
    />
  );
};
