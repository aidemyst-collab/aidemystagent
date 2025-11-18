import { ExportOutlined } from '@ant-design/icons';
import { BaseNode } from './BaseNode';
import { NodeProps } from 'reactflow';

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
