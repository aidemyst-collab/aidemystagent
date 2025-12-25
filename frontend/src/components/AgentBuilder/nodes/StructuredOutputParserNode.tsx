import { CheckCircleOutlined } from '@ant-design/icons';
import { BaseNode } from './BaseNode';
import type { NodeProps } from '@xyflow/react';

export const StructuredOutputParserNode = (props: NodeProps) => {
  return (
    <BaseNode
      {...props}
      icon={<CheckCircleOutlined />}
      color="#9333EA"
      hasInput={true}
      hasOutput={true}
      minWidth={180}
    />
  );
};
