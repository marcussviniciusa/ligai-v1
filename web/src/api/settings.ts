import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchApi } from './client';
import type { Setting, TestApiKeyResponse } from './client';

export function useSettings() {
  return useQuery({
    queryKey: ['settings'],
    queryFn: () => fetchApi<Setting[]>('/settings'),
  });
}

export function useUpdateSetting() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      fetchApi<Setting>(`/settings/${key}`, {
        method: 'PUT',
        body: JSON.stringify({ value }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
  });
}

export function useTestApiKey() {
  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      fetchApi<TestApiKeyResponse>('/settings/test', {
        method: 'POST',
        body: JSON.stringify({ key, value }),
      }),
  });
}

export function useReloadSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      fetchApi<{ success: boolean; message: string }>('/settings/reload', {
        method: 'POST',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
  });
}
