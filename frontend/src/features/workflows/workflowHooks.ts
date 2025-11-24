import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { workflowService } from './workflowService';
import { message } from 'antd';

export const useCreateWorkflow = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data) => {
      console.log('useCreateWorkflow mutationFn called with:', data);
      return workflowService.createWorkflow(data);
    },
    onSuccess: (data) => {
      console.log('useCreateWorkflow onSuccess:', data);
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      message.success(`Workflow "${data.name}" saved successfully!`);
    },
    onError: (error: any) => {
      console.log('useCreateWorkflow onError:', error);
      message.error(error.message || 'Failed to save workflow');
    },
  });
};

export const useUpdateWorkflow = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => {
      console.log('useUpdateWorkflow mutationFn called with id:', id, 'data:', data);
      return workflowService.updateWorkflow(id, data);
    },
    onSuccess: (data) => {
      console.log('useUpdateWorkflow onSuccess:', data);
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      queryClient.invalidateQueries({ queryKey: ['workflow', data.id] });
      message.success(`Workflow "${data.name}" updated successfully!`);
    },
    onError: (error: any) => {
      console.log('useUpdateWorkflow onError:', error);
      message.error(error.message || 'Failed to update workflow');
    },
  });
};

export const useDeployWorkflow = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: workflowService.deployWorkflow,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      queryClient.invalidateQueries({ queryKey: ['workflow', data.id] });
      message.success(`Workflow deployed! Endpoint: ${data.endpoint}`);
    },
    onError: (error: any) => {
      message.error(error.message || 'Failed to deploy workflow');
    },
  });
};

export const useWorkflow = (id: string | null) => {
  return useQuery({
    queryKey: ['workflow', id],
    queryFn: () => workflowService.getWorkflow(id!),
    enabled: !!id,
  });
};

export const useWorkflows = () => {
  return useQuery({
    queryKey: ['workflows'],
    queryFn: workflowService.getWorkflows,
  });
};

export const useDeleteWorkflow = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: workflowService.deleteWorkflow,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows'] });
      message.success('Workflow deleted successfully!');
    },
    onError: (error: any) => {
      message.error(error.message || 'Failed to delete workflow');
    },
  });
};

export const useExecuteWorkflow = () => {
  return useMutation({
    mutationFn: ({ id, input }: { id: string; input: string }) =>
      workflowService.executeWorkflow(id, input),
    onError: (error: any) => {
      message.error(error.message || 'Failed to execute workflow');
    },
  });
};
