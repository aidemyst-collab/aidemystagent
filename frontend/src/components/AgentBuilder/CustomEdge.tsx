import { BaseEdge, EdgeLabelRenderer, getBezierPath, useReactFlow } from '@xyflow/react';
import { CloseCircleOutlined } from '@ant-design/icons';

interface CustomEdgeProps {
  id: string;
  sourceX: number;
  sourceY: number;
  targetX: number;
  targetY: number;
  sourcePosition: any;
  targetPosition: any;
  style?: React.CSSProperties;
  markerEnd?: string;
  selected?: boolean;
}

export const CustomEdge = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  selected,
}: CustomEdgeProps) => {
  const { setEdges } = useReactFlow();
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const onEdgeClick = () => {
    setEdges((edges) => edges.filter((edge) => edge.id !== id));
  };

  return (
    <>
      <BaseEdge path={edgePath} markerEnd={markerEnd} style={style} />
      {selected && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: 'absolute',
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              fontSize: 20,
              pointerEvents: 'all',
              cursor: 'pointer',
            }}
            className="nodrag nopan"
          >
            <CloseCircleOutlined
              onClick={onEdgeClick}
              style={{
                background: 'white',
                borderRadius: '50%',
                color: '#ff4d4f',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = '#cf1322';
                e.currentTarget.style.transform = 'scale(1.2)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = '#ff4d4f';
                e.currentTarget.style.transform = 'scale(1)';
              }}
            />
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
};
