import { apiClient } from '../../services/api';

export interface DashboardStats {
  totalAgents: number;
  deployedAgents: number;
  totalExecutions: number;
  activeUsers: number;
  executionsToday: number;
  executionsThisWeek: number;
}

export interface RecentActivity {
  id: string;
  type?: 'agent_created' | 'agent_deployed' | 'agent_executed';
  agent_id: string;
  agent_name: string;
  created_at: string;
  tokens_used?: number;
  execution_time?: number;
}

export const dashboardService = {
  /**
   * Get dashboard statistics
   */
  getStats: async (): Promise<DashboardStats> => {
    return apiClient.get<DashboardStats>('/dashboard/stats');
  },

  /**
   * Get recent activity
   */
  getRecentActivity: async (limit: number = 10): Promise<RecentActivity[]> => {
    return apiClient.get<RecentActivity[]>(`/dashboard/activity?limit=${limit}`);
  },
};
