import { useQuery } from '@tanstack/react-query';
import { dashboardService } from './dashboardService';

export const useDashboardStats = () => {
  return useQuery({
    queryKey: ['dashboard', 'stats'],
    queryFn: dashboardService.getStats,
    refetchInterval: 30000, // Refetch every 30 seconds
  });
};

export const useRecentActivity = (limit: number = 10) => {
  return useQuery({
    queryKey: ['dashboard', 'activity', limit],
    queryFn: () => dashboardService.getRecentActivity(limit),
    refetchInterval: 10000, // Refetch every 10 seconds
  });
};
