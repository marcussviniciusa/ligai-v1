import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchApi } from './client';
import type { Prompt } from './client';

export function usePrompts() {
  return useQuery({
    queryKey: ['prompts'],
    queryFn: () => fetchApi<Prompt[]>('/prompts'),
  });
}

export function usePrompt(id: number) {
  return useQuery({
    queryKey: ['prompts', id],
    queryFn: () => fetchApi<Prompt>(`/prompts/${id}`),
    enabled: !!id,
  });
}

export function useActivePrompt() {
  return useQuery({
    queryKey: ['prompts', 'active'],
    queryFn: () => fetchApi<Prompt | null>('/prompts/active'),
  });
}

export function useCreatePrompt() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Omit<Prompt, 'id' | 'created_at' | 'updated_at' | 'is_active'>) =>
      fetchApi<Prompt>('/prompts', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompts'] });
    },
  });
}

export function useUpdatePrompt() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Prompt> }) =>
      fetchApi<Prompt>(`/prompts/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompts'] });
    },
  });
}

export function useDeletePrompt() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) =>
      fetchApi<void>(`/prompts/${id}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompts'] });
    },
  });
}

export function useActivatePrompt() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) =>
      fetchApi<Prompt>(`/prompts/${id}/activate`, {
        method: 'POST',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['prompts'] });
    },
  });
}
