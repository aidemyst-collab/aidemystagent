import { ApartmentOutlined } from '@ant-design/icons';
import { BaseNode } from './BaseNode';
import { NodeProps } from '@xyflow/react';

export const SubgraphNode = (props: NodeProps) => {
  return (
    <BaseNode
      {...props}
      icon={<ApartmentOutlined />}
      color="#eb2f96"
    />
  );
};
