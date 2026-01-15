import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchApi } from './client';

export interface ScheduledCall {
  id: number;
  phone_number: string;
  prompt_id: number | null;
  scheduled_time: string;
  status: string;
  call_id: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateScheduledCallData {
  phone_number: string;
  scheduled_time: string;
  prompt_id?: number;
  notes?: string;
}

export function useScheduledCalls(status?: string) {
  return useQuery({
    queryKey: ['schedules', status],
    queryFn: () => {
      const params = new URLSearchParams();
      if (status) params.append('status', status);
      const query = params.toString();
      return fetchApi<ScheduledCall[]>(`/schedules${query ? `?${query}` : ''}`);
    },
  });
}

export function useCreateScheduledCall() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateScheduledCallData) =>
      fetchApi<ScheduledCall>('/schedules', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
  });
}

export function useCancelScheduledCall() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) =>
      fetchApi<void>(`/schedules/${id}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedules'] });
    },
  });
}
