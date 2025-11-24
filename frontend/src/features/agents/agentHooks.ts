import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { agentService } from './agentService';
import { message } from 'antd';

export const useCreateAgent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data) => {
      console.log('useCreateAgent mutationFn called with:', data);
      return agentService.createAgent(data);
    },
    onSuccess: (data) => {
      console.log('useCreateAgent onSuccess:', data);
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      message.success(`Agent "${data.name}" saved successfully!`);
    },
    onError: (error: any) => {
      console.log('useCreateAgent onError:', error);
      message.error(error.message || 'Failed to save agent');
    },
  });
};

export const useUpdateAgent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => {
      console.log('useUpdateAgent mutationFn called with id:', id, 'data:', data);
      return agentService.updateAgent(id, data);
    },
    onSuccess: (data) => {
      console.log('useUpdateAgent onSuccess:', data);
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      queryClient.invalidateQueries({ queryKey: ['agent', data.id] });
      message.success(`Agent "${data.name}" updated successfully!`);
    },
    onError: (error: any) => {
      console.log('useUpdateAgent onError:', error);
      message.error(error.message || 'Failed to update agent');
    },
  });
};

export const useDeployAgent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: agentService.deployAgent,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      queryClient.invalidateQueries({ queryKey: ['agent', data.id] });
      message.success(`Agent deployed! Endpoint: ${data.endpoint}`);
    },
    onError: (error: any) => {
      message.error(error.message || 'Failed to deploy agent');
    },
  });
};

export const useAgent = (id: string | null) => {
  return useQuery({
    queryKey: ['agent', id],
    queryFn: () => agentService.getAgent(id!),
    enabled: !!id,
  });
};

export const useAgents = () => {
  return useQuery({
    queryKey: ['agents'],
    queryFn: agentService.getAgents,
  });
};

export const useDeleteAgent = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: agentService.deleteAgent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      message.success('Agent deleted successfully!');
    },
    onError: (error: any) => {
      message.error(error.message || 'Failed to delete agent');
    },
  });
};

export const useExecuteAgent = () => {
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: string }) =>
      agentService.executeAgent(id, input),
    onError: (error: any) => {
      message.error(error.message || 'Failed to execute agent');
    },
  });
};
