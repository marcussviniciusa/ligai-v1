import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchApi } from './client';

export interface Campaign {
  id: number;
  name: string;
  description: string | null;
  prompt_id: number | null;
  status: string;
  max_concurrent: number;
  total_contacts: number;
  completed_contacts: number;
  failed_contacts: number;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface CampaignContact {
  id: number;
  phone_number: string;
  name: string | null;
  status: string;
  call_id: string | null;
  attempts: number;
  last_attempt_at: string | null;
  completed_at: string | null;
  error_message: string | null;
}

export interface CampaignStats {
  total: number;
  pending: number;
  calling: number;
  completed: number;
  failed: number;
  success_rate: number;
}

export interface CreateCampaignData {
  name: string;
  description?: string;
  prompt_id?: number;
  max_concurrent?: number;
}

export interface UpdateCampaignData {
  name?: string;
  description?: string;
  prompt_id?: number;
  max_concurrent?: number;
}

export interface ImportContactsData {
  contacts: Array<{ phone_number: string; name?: string }>;
}

export function useCampaigns(status?: string) {
  return useQuery({
    queryKey: ['campaigns', status],
    queryFn: () => {
      const params = new URLSearchParams();
      if (status) params.append('status', status);
      const query = params.toString();
      return fetchApi<Campaign[]>(`/campaigns${query ? `?${query}` : ''}`);
    },
  });
}

export function useCampaign(id: number) {
  return useQuery({
    queryKey: ['campaigns', id],
    queryFn: () => fetchApi<Campaign>(`/campaigns/${id}`),
    enabled: !!id,
  });
}

export function useCreateCampaign() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateCampaignData) =>
      fetchApi<Campaign>('/campaigns', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });
}

export function useUpdateCampaign() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateCampaignData }) =>
      fetchApi<Campaign>(`/campaigns/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      queryClient.invalidateQueries({ queryKey: ['campaigns', variables.id] });
    },
  });
}

export function useDeleteCampaign() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) =>
      fetchApi<void>(`/campaigns/${id}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });
}

export function useStartCampaign() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) =>
      fetchApi<{ success: boolean; message: string }>(`/campaigns/${id}/start`, {
        method: 'POST',
      }),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      queryClient.invalidateQueries({ queryKey: ['campaigns', id] });
    },
  });
}

export function usePauseCampaign() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) =>
      fetchApi<{ success: boolean; message: string }>(`/campaigns/${id}/pause`, {
        method: 'POST',
      }),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      queryClient.invalidateQueries({ queryKey: ['campaigns', id] });
    },
  });
}

export function useCampaignStats(id: number) {
  return useQuery({
    queryKey: ['campaigns', id, 'stats'],
    queryFn: () => fetchApi<CampaignStats>(`/campaigns/${id}/stats`),
    enabled: !!id,
    refetchInterval: 5000,
  });
}

export function useCampaignContacts(
  id: number,
  page: number = 1,
  perPage: number = 50,
  status?: string
) {
  return useQuery({
    queryKey: ['campaigns', id, 'contacts', page, perPage, status],
    queryFn: () => {
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: perPage.toString(),
      });
      if (status) params.append('status', status);
      return fetchApi<CampaignContact[]>(`/campaigns/${id}/contacts?${params}`);
    },
    enabled: !!id,
  });
}

export function useImportContacts() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ImportContactsData }) =>
      fetchApi<{ success: boolean; imported: number }>(`/campaigns/${id}/contacts`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns', variables.id] });
      queryClient.invalidateQueries({
        queryKey: ['campaigns', variables.id, 'contacts'],
      });
    },
  });
}

export function useImportContactsCsv() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, file }: { id: number; file: File }) => {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`/api/v1/campaigns/${id}/contacts/csv`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
      }

      return response.json() as Promise<{ success: boolean; imported: number }>;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['campaigns', variables.id] });
      queryClient.invalidateQueries({
        queryKey: ['campaigns', variables.id, 'contacts'],
      });
    },
  });
}
