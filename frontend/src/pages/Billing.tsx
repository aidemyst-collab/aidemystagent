import React, { useEffect, useState } from 'react';
import {
  Card, Row, Col, Tag, Button, Typography, Space, Table, Switch,
  Alert, Divider, Spin, message, Badge,
} from 'antd';
import {
  CheckCircleOutlined, CloseCircleOutlined, CrownOutlined,
  CreditCardOutlined, FileTextOutlined, SyncOutlined,
  DatabaseOutlined, ApiOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { billingService, PlanInfo } from '../features/billing/billingService';
import { usePermissions } from '../features/auth/authStore';

const { Title, Text } = Typography;

const STATUS_COLOR: Record<string, string> = {
  active: 'success',
  trialing: 'processing',
  past_due: 'warning',
  canceled: 'default',
  suspended: 'error',
};

const PLAN_RANK: Record<string, number> = { free: 0, starter: 1, professional: 2, enterprise: 3 };

function formatAed(cents: number): string {
  if (cents === 0) return 'AED 0';
  return `AED ${(cents / 100).toLocaleString('en-AE', { minimumFractionDigits: 0 })}`;
}

export const Billing: React.FC = () => {
  const { isOrgAdmin, isPlatformAdmin } = usePermissions();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [annual, setAnnual] = useState(false);

  const canManage = isOrgAdmin || isPlatformAdmin;

  // Handle success redirect from Stripe Checkout
  useEffect(() => {
    if (searchParams.get('success') === '1') {
      message.success('Payment successful! Your plan is being activated…');
      setSearchParams({}, { replace: true });
      // Pass current plan so polling knows when the webhook has updated the DB
      billingService.refreshTokenAfterUpgrade(subData?.plan ?? 'free').then(() => {
        queryClient.invalidateQueries({ queryKey: ['billing', 'subscription'] });
        message.success('Your new plan is active! New product links have been added to the sidebar.');
      });
    }
  }, []);

  const { data: subData, isLoading: subLoading } = useQuery({
    queryKey: ['billing', 'subscription'],
    queryFn: billingService.getSubscription,
  });

  const { data: plansData, isLoading: plansLoading } = useQuery({
    queryKey: ['billing', 'plans'],
    queryFn: billingService.getPlans,
  });

  const { data: invoiceData } = useQuery({
    queryKey: ['billing', 'invoices'],
    queryFn: () => billingService.getInvoices(10),
  });

  const checkoutMutation = useMutation({
    mutationFn: ({ priceId }: { priceId: string }) =>
      billingService.createCheckoutSession(priceId, annual),
    onSuccess: (data) => { window.location.href = data.url; },
    onError: (err: Error) => message.error(err.message),
  });

  const portalMutation = useMutation({
    mutationFn: billingService.createPortalSession,
    onSuccess: (data) => { window.location.href = data.url; },
    onError: () => message.error('Failed to open billing portal'),
  });

  const cancelMutation = useMutation({
    mutationFn: billingService.cancelSubscription,
    onSuccess: () => {
      message.success('Subscription will cancel at the end of the billing period');
      queryClient.invalidateQueries({ queryKey: ['billing', 'subscription'] });
    },
    onError: () => message.error('Failed to cancel subscription'),
  });

  const reactivateMutation = useMutation({
    mutationFn: billingService.reactivateSubscription,
    onSuccess: () => {
      message.success('Subscription reactivated');
      queryClient.invalidateQueries({ queryKey: ['billing', 'subscription'] });
    },
    onError: () => message.error('Failed to reactivate subscription'),
  });

  if (subLoading || plansLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}>
        <Spin size="large" />
      </div>
    );
  }

  const currentPlan = subData?.plan ?? 'free';
  const currentRank = PLAN_RANK[currentPlan] ?? 0;

  const getPriceId = (plan: PlanInfo) =>
    annual ? plan.stripe_price_id_annual : plan.stripe_price_id_monthly;

  const getDisplayPrice = (plan: PlanInfo) => {
    if (plan.price_monthly_aed === 0) return 'Free';
    const price = annual
      ? Math.round(plan.price_annual_aed / 12)
      : plan.price_monthly_aed;
    return `AED ${price}`;
  };

  return (
    <div style={{ padding: '24px', maxWidth: 1200 }}>
      <Title level={2} style={{ marginBottom: 8 }}>
        <CreditCardOutlined style={{ marginRight: 8 }} />
        Billing & Plans
      </Title>
      <Text type="secondary">Manage your AgentStudio subscription.</Text>

      <Divider />

      {/* Current Plan Banner */}
      <Card
        style={{ marginBottom: 24, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', border: 'none' }}
        styles={{ body: { padding: '20px 24px' } }}
      >
        <Row align="middle" justify="space-between" wrap>
          <Col>
            <Space direction="vertical" size={4}>
              <Text style={{ color: 'rgba(255,255,255,0.8)', fontSize: 13 }}>Current Plan</Text>
              <Space align="center">
                <CrownOutlined style={{ color: '#ffd700', fontSize: 22 }} />
                <Title level={3} style={{ color: '#fff', margin: 0, textTransform: 'capitalize' }}>
                  {currentPlan}
                </Title>
                <Tag color={STATUS_COLOR[subData?.status ?? 'trialing'] ?? 'default'} style={{ textTransform: 'capitalize' }}>
                  {subData?.status ?? 'trialing'}
                </Tag>
              </Space>
              {subData?.current_period_end && (
                <Text style={{ color: 'rgba(255,255,255,0.7)', fontSize: 12 }}>
                  {subData.cancel_at_period_end ? 'Cancels' : 'Renews'} on{' '}
                  {new Date(subData.current_period_end).toLocaleDateString('en-AE', { day: 'numeric', month: 'long', year: 'numeric' })}
                </Text>
              )}
            </Space>
          </Col>
          {canManage && (
            <Col>
              <Space>
                {subData?.cancel_at_period_end ? (
                  <Button
                    onClick={() => reactivateMutation.mutate()}
                    loading={reactivateMutation.isPending}
                    icon={<SyncOutlined />}
                  >
                    Reactivate
                  </Button>
                ) : subData?.stripe_subscription_id ? (
                  <>
                    <Button
                      ghost
                      onClick={() => portalMutation.mutate()}
                      loading={portalMutation.isPending}
                    >
                      Manage Billing
                    </Button>
                    <Button
                      danger ghost
                      onClick={() => cancelMutation.mutate()}
                      loading={cancelMutation.isPending}
                    >
                      Cancel Plan
                    </Button>
                  </>
                ) : null}
              </Space>
            </Col>
          )}
        </Row>
      </Card>

      {subData?.cancel_at_period_end && (
        <Alert
          type="warning"
          showIcon
          message="Your subscription is set to cancel at the end of the current billing period. Reactivate to keep access."
          style={{ marginBottom: 24 }}
        />
      )}

      {/* Add-on products callout — shown when the current plan includes DemystRAG or Mock API */}
      {(plansData?.plans ?? []).find(p => p.key === currentPlan)?.has_demystrag && (
        <Alert
          type="info"
          showIcon
          icon={<DatabaseOutlined />}
          style={{ marginBottom: 12 }}
          message={
            <span>
              <strong>DemystRAG</strong> is included in your plan —{' '}
              find the link in the left sidebar under <strong>Add-ons</strong>.
            </span>
          }
        />
      )}
      {(plansData?.plans ?? []).find(p => p.key === currentPlan)?.has_mock_api && (
        <Alert
          type="success"
          showIcon
          icon={<ApiOutlined />}
          style={{ marginBottom: 24 }}
          message={
            <span>
              <strong>Mock API</strong> is included in your plan —{' '}
              find the link in the left sidebar under <strong>Add-ons</strong>.
            </span>
          }
        />
      )}

      {/* Billing toggle */}
      <Row align="middle" style={{ marginBottom: 20 }} gutter={12}>
        <Col><Text strong>Monthly</Text></Col>
        <Col>
          <Switch checked={annual} onChange={setAnnual} />
        </Col>
        <Col>
          <Text strong>Annual</Text>{' '}
          <Tag color="green">Save 17%</Tag>
        </Col>
      </Row>

      {/* Plan Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 40 }}>
        {(plansData?.plans ?? []).map((plan) => {
          const planRank = PLAN_RANK[plan.key] ?? 0;
          const isCurrent = plan.key === currentPlan;
          const isUpgrade = planRank > currentRank;
          const isPopular = plan.key === 'professional';
          const priceId = getPriceId(plan);

          return (
            <Col xs={24} sm={12} lg={6} key={plan.key}>
              <Badge.Ribbon text="Most Popular" color="purple" style={{ display: isPopular ? undefined : 'none' }}>
                <Card
                  bordered
                  style={{
                    height: '100%',
                    border: isCurrent ? '2px solid #667eea' : isPopular ? '2px solid #722ed1' : undefined,
                  }}
                  styles={{ body: { padding: 20, display: 'flex', flexDirection: 'column', height: '100%' } }}
                >
                  <div style={{ flex: 1 }}>
                    <Space direction="vertical" size={4} style={{ width: '100%', marginBottom: 12 }}>
                      <Title level={4} style={{ margin: 0, textTransform: 'capitalize' }}>{plan.name}</Title>
                      <div>
                        <Text style={{ fontSize: 28, fontWeight: 700 }}>{getDisplayPrice(plan)}</Text>
                        {plan.price_monthly_aed > 0 && (
                          <Text type="secondary" style={{ fontSize: 13 }}> / month</Text>
                        )}
                      </div>
                      {annual && plan.price_annual_aed > 0 && (
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          AED {plan.price_annual_aed.toLocaleString()} / year
                        </Text>
                      )}
                    </Space>

                    <ul style={{ paddingLeft: 0, listStyle: 'none', margin: '12px 0' }}>
                      {plan.features
                        .filter((f) => !f.startsWith('DemystRAG') && !f.startsWith('Mock API'))
                        .map((f) => (
                          <li key={f} style={{ display: 'flex', gap: 8, marginBottom: 6, fontSize: 13 }}>
                            <CheckCircleOutlined style={{ color: '#52c41a', marginTop: 2, flexShrink: 0 }} />
                            <span>{f}</span>
                          </li>
                        ))}
                    </ul>

                    {(plan.has_demystrag || plan.has_mock_api) && (
                      <div style={{ marginTop: 4, marginBottom: 12 }}>
                        <Text style={{ fontSize: 11, fontWeight: 600, color: '#8c8c8c', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                          Included Add-ons
                        </Text>
                        <div style={{ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 6 }}>
                          {plan.has_demystrag && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 10px', background: '#e6f7ff', borderRadius: 8, border: '1px solid #91d5ff' }}>
                              <DatabaseOutlined style={{ color: '#1890ff', fontSize: 15 }} />
                              <div>
                                <Text strong style={{ fontSize: 12, color: '#003a8c' }}>DemystRAG</Text>
                                <Text style={{ fontSize: 11, color: '#096dd9', display: 'block' }}>
                                  {plan.key === 'enterprise' ? 'Unlimited docs & storage' : '2,000 documents · 20 GB'}
                                </Text>
                              </div>
                            </div>
                          )}
                          {plan.has_mock_api && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '7px 10px', background: '#f6ffed', borderRadius: 8, border: '1px solid #b7eb8f' }}>
                              <ApiOutlined style={{ color: '#52c41a', fontSize: 15 }} />
                              <div>
                                <Text strong style={{ fontSize: 12, color: '#135200' }}>Mock API</Text>
                                <Text style={{ fontSize: 11, color: '#389e0d', display: 'block' }}>
                                  {plan.key === 'enterprise' ? 'Full access' : 'Configurable testing'}
                                </Text>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>

                  {canManage && (
                    <div style={{ marginTop: 16 }}>
                      {isCurrent ? (
                        <Button block disabled>Current Plan</Button>
                      ) : plan.key === 'enterprise' ? (
                        <Button block href="mailto:sales@aidemyst.com">Contact Sales</Button>
                      ) : isUpgrade ? (
                        <Button
                          block
                          type={isPopular ? 'primary' : 'default'}
                          disabled={!priceId}
                          onClick={() => priceId && checkoutMutation.mutate({ priceId })}
                          loading={checkoutMutation.isPending && checkoutMutation.variables?.priceId === priceId}
                        >
                          Upgrade
                        </Button>
                      ) : (
                        <Button block disabled>Downgrade via Portal</Button>
                      )}
                    </div>
                  )}
                </Card>
              </Badge.Ribbon>
            </Col>
          );
        })}
      </Row>

      {/* Invoices */}
      {invoiceData && invoiceData.invoices.length > 0 && (
        <>
          <Title level={4}>
            <FileTextOutlined style={{ marginRight: 8 }} />
            Invoice History
          </Title>
          <Table
            dataSource={invoiceData.invoices}
            rowKey="id"
            pagination={false}
            size="small"
            columns={[
              {
                title: 'Invoice',
                dataIndex: 'number',
                render: (num: string) => num || '—',
              },
              {
                title: 'Period',
                render: (_: unknown, row) =>
                  row.period_start && row.period_end
                    ? `${new Date(row.period_start).toLocaleDateString('en-AE')} – ${new Date(row.period_end).toLocaleDateString('en-AE')}`
                    : '—',
              },
              {
                title: 'Amount',
                dataIndex: 'amount_paid',
                render: (cents: number, row) =>
                  `${row.currency.toUpperCase()} ${(cents / 100).toFixed(2)}`,
              },
              {
                title: 'Status',
                dataIndex: 'status',
                render: (s: string) => (
                  <Tag color={s === 'paid' ? 'success' : 'warning'} style={{ textTransform: 'capitalize' }}>
                    {s}
                  </Tag>
                ),
              },
              {
                title: '',
                render: (_: unknown, row) =>
                  row.hosted_invoice_url ? (
                    <a href={row.hosted_invoice_url} target="_blank" rel="noopener noreferrer">
                      View
                    </a>
                  ) : null,
              },
            ]}
          />
        </>
      )}
    </div>
  );
};

export default Billing;
