import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchApi } from './client';

export interface WebhookConfig {
  id: number;
  url: string;
  events: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WebhookLog {
  id: number;
  event_type: string;
  status_code: number | null;
  success: boolean;
  attempt: number;
  error_message: string | null;
  created_at: string;
}

export interface CreateWebhookData {
  url: string;
  events: string[];
  secret?: string;
}

export interface UpdateWebhookData {
  url?: string;
  events?: string[];
  is_active?: boolean;
  secret?: string;
}

export function useWebhooks() {
  return useQuery({
    queryKey: ['webhooks'],
    queryFn: () => fetchApi<WebhookConfig[]>('/webhooks'),
  });
}

export function useWebhookEvents() {
  return useQuery({
    queryKey: ['webhooks', 'events'],
    queryFn: () => fetchApi<{ events: string[] }>('/webhooks/events'),
  });
}

export function useCreateWebhook() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateWebhookData) =>
      fetchApi<WebhookConfig>('/webhooks', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] });
    },
  });
}

export function useUpdateWebhook() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateWebhookData }) =>
      fetchApi<WebhookConfig>(`/webhooks/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] });
    },
  });
}

export function useDeleteWebhook() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) =>
      fetchApi<void>(`/webhooks/${id}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks'] });
    },
  });
}

export function useWebhookLogs(webhookId: number) {
  return useQuery({
    queryKey: ['webhooks', webhookId, 'logs'],
    queryFn: () => fetchApi<WebhookLog[]>(`/webhooks/${webhookId}/logs`),
    enabled: !!webhookId,
  });
}

export function useTestWebhook() {
  return useMutation({
    mutationFn: (id: number) =>
      fetchApi<{ success: boolean; status_code?: number; message: string }>(
        `/webhooks/${id}/test`,
        { method: 'POST' }
      ),
  });
}
