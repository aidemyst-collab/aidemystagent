import React from 'react';
import { Card, Progress, Skeleton, Tag, Typography } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../services/api';

const { Text } = Typography;

interface QuotaItem {
  current: number;
  limit: number;
  percentage: number;
  unlimited: boolean;
}

interface UsageData {
  plan: { name: string; display_name: string; features: Record<string, boolean> };
  usage: {
    agents: QuotaItem;
    users: QuotaItem;
    deployments: QuotaItem;
    tools: QuotaItem;
    credentials: QuotaItem;
    executions_this_month: QuotaItem;
  };
}

const getStrokeColor = (percentage: number): string => {
  if (percentage >= 90) return '#ff4d4f';
  if (percentage >= 70) return '#faad14';
  return '#52c41a';
};

const getLimitTag = (percentage: number): React.ReactNode => {
  if (percentage >= 90) {
    return (
      <Tag color="error" style={{ marginLeft: 8, fontSize: 11 }}>
        Limit reached
      </Tag>
    );
  }
  if (percentage >= 70) {
    return (
      <Tag color="warning" style={{ marginLeft: 8, fontSize: 11 }}>
        Near limit
      </Tag>
    );
  }
  return null;
};

interface QuotaRowProps {
  label: string;
  item: QuotaItem;
}

const QuotaRow: React.FC<QuotaRowProps> = ({ label, item }) => {
  const displayValue = item.unlimited ? 'Unlimited' : `${item.current} / ${item.limit}`;
  const percent = item.unlimited ? 0 : Math.min(item.percentage, 100);

  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <Text style={{ fontSize: 13 }}>
          {label}
          {!item.unlimited && getLimitTag(item.percentage)}
        </Text>
        <Text strong style={{ fontSize: 13, whiteSpace: 'nowrap', marginLeft: 8 }}>
          {displayValue}
        </Text>
      </div>
      {!item.unlimited && (
        <Progress
          percent={percent}
          showInfo={false}
          strokeColor={getStrokeColor(item.percentage)}
          size="small"
        />
      )}
    </div>
  );
};

export const QuotaUsage: React.FC = () => {
  const { data, isLoading, isError } = useQuery<UsageData>({
    queryKey: ['org-usage'],
    queryFn: () => apiClient.get<UsageData>('/organizations/me/usage'),
  });

  if (isError) {
    return null;
  }

  const skeletonRows = Array.from({ length: 6 });

  return (
    <Card
      title="Plan Usage"
      extra={
        isLoading ? null : (
          <Text type="secondary" style={{ fontSize: 12 }}>
            {data?.plan.display_name}
          </Text>
        )
      }
    >
      {isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {skeletonRows.map((_, i) => (
            <Skeleton.Input key={i} active style={{ width: '100%', height: 20 }} />
          ))}
        </div>
      ) : data ? (
        <>
          <QuotaRow label="Agents" item={data.usage.agents} />
          <QuotaRow label="Users" item={data.usage.users} />
          <QuotaRow label="Deployments" item={data.usage.deployments} />
          <QuotaRow label="Tools" item={data.usage.tools} />
          <QuotaRow label="Credentials" item={data.usage.credentials} />
          <QuotaRow label="Executions (this month)" item={data.usage.executions_this_month} />
        </>
      ) : null}
    </Card>
  );
};
