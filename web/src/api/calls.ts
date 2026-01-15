import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchApi } from './client';
import type { ActiveCall, Call, CallsListResponse, Stats } from './client';

export function useActiveCalls() {
  return useQuery({
    queryKey: ['calls', 'active'],
    queryFn: () => fetchApi<ActiveCall[]>('/calls/active'),
    refetchInterval: 3000, // Refresh every 3 seconds
  });
}

export function useStats() {
  return useQuery({
    queryKey: ['stats'],
    queryFn: () => fetchApi<Stats>('/stats'),
    refetchInterval: 5000,
  });
}

export function useCalls(page: number = 1, perPage: number = 20, status?: string) {
  return useQuery({
    queryKey: ['calls', 'history', page, perPage, status],
    queryFn: () => {
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: perPage.toString(),
      });
      if (status) params.append('status', status);
      return fetchApi<CallsListResponse>(`/calls?${params}`);
    },
  });
}

export function useCall(id: number) {
  return useQuery({
    queryKey: ['calls', id],
    queryFn: () => fetchApi<Call>(`/calls/${id}`),
    enabled: !!id,
  });
}

export function useHangupCall() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (callId: string) =>
      fetchApi<{ success: boolean; message: string }>(`/calls/${callId}/hangup`, {
        method: 'POST',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calls', 'active'] });
    },
  });
}

export function useDialCall() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: { number: string; prompt_id?: number }) =>
      fetchApi<{ success: boolean; call_id?: string; message: string }>('/calls/dial', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calls', 'active'] });
    },
  });
}

export function useDeleteCall() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) =>
      fetchApi<void>(`/calls/${id}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['calls', 'history'] });
    },
  });
}
