import { getApiUrl } from '../../config/api';
import { useAuthStore } from '../auth/authStore';

export interface PlanInfo {
  key: string;
  name: string;
  price_monthly_aed: number;
  price_annual_aed: number;
  stripe_price_id_monthly: string;
  stripe_price_id_annual: string;
  max_users: number;
  max_agents: number;
  max_deployments: number;
  max_executions: number;
  has_demystrag: boolean;
  has_mock_api: boolean;
  features: string[];
}

export interface SubscriptionInfo {
  plan: string;
  status: string;
  stripe_subscription_id: string | null;
  stripe_price_id: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  trial_end: string | null;
  max_users: number;
  max_agents: number;
  max_deployments: number;
  max_executions: number;
}

export interface Invoice {
  id: string;
  number: string;
  amount_paid: number;
  currency: string;
  status: string;
  hosted_invoice_url: string | null;
  invoice_pdf: string | null;
  period_start: string | null;
  period_end: string | null;
}

async function authFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = useAuthStore.getState().tokens?.accessToken;
  return fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });
}

export const billingService = {
  async getSubscription(): Promise<SubscriptionInfo> {
    const res = await authFetch(getApiUrl('/billing/subscription'));
    if (!res.ok) throw new Error('Failed to fetch subscription');
    return res.json();
  },

  async getPlans(): Promise<{ plans: PlanInfo[] }> {
    const res = await fetch(getApiUrl('/billing/plans'));
    if (!res.ok) throw new Error('Failed to fetch plans');
    return res.json();
  },

  async createCheckoutSession(priceId: string, annual: boolean): Promise<{ url: string }> {
    const base = window.location.origin;
    const res = await authFetch(getApiUrl('/billing/checkout'), {
      method: 'POST',
      body: JSON.stringify({
        price_id: priceId,
        success_url: `${base}/billing?success=1`,
        cancel_url: `${base}/billing`,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to create checkout session');
    }
    return res.json();
  },

  async createPortalSession(): Promise<{ url: string }> {
    const res = await authFetch(getApiUrl('/billing/portal'), {
      method: 'POST',
      body: JSON.stringify({ return_url: `${window.location.origin}/billing` }),
    });
    if (!res.ok) throw new Error('Failed to create portal session');
    return res.json();
  },

  async cancelSubscription(): Promise<SubscriptionInfo> {
    const res = await authFetch(getApiUrl('/billing/cancel'), { method: 'POST' });
    if (!res.ok) throw new Error('Failed to cancel subscription');
    return res.json();
  },

  async reactivateSubscription(): Promise<SubscriptionInfo> {
    const res = await authFetch(getApiUrl('/billing/reactivate'), { method: 'POST' });
    if (!res.ok) throw new Error('Failed to reactivate subscription');
    return res.json();
  },

  async getInvoices(limit = 10): Promise<{ invoices: Invoice[]; has_more: boolean }> {
    const res = await authFetch(getApiUrl(`/billing/invoices?limit=${limit}`));
    if (!res.ok) throw new Error('Failed to fetch invoices');
    return res.json();
  },

  /**
   * Re-issue JWT with updated plan after Stripe checkout returns.
   * Polls /billing/subscription until the backend has processed the Stripe
   * webhook and the plan name changes, then refreshes the access token so
   * hasProduct() picks up the newly unlocked products immediately.
   */
  async refreshTokenAfterUpgrade(previousPlan = 'free'): Promise<void> {
    const { tokens, updateTokens } = useAuthStore.getState();
    if (!tokens?.refreshToken) return;

    // Wait for the Stripe webhook to be processed (up to 15s, polling every 2s)
    const MAX_ATTEMPTS = 8;
    for (let i = 0; i < MAX_ATTEMPTS; i++) {
      await new Promise(resolve => setTimeout(resolve, 2000));
      try {
        const subRes = await authFetch(getApiUrl('/billing/subscription'));
        if (subRes.ok) {
          const sub: SubscriptionInfo = await subRes.json();
          if (sub.plan !== previousPlan) break; // webhook processed — plan updated
        }
      } catch {
        // ignore network errors during polling
      }
    }

    // Refresh the JWT so it carries the updated products[] claim
    const res = await fetch(getApiUrl('/auth/refresh'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: tokens.refreshToken }),
    });
    if (res.ok) {
      const data = await res.json();
      if (data.access_token) {
        updateTokens({ accessToken: data.access_token, refreshToken: tokens.refreshToken });
      }
    }
  },
};
