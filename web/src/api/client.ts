const API_BASE = '/api/v1';

export async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// Types
export interface Prompt {
  id: number;
  name: string;
  description: string | null;
  system_prompt: string;
  voice_id: string;
  llm_model: string;
  temperature: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ActiveCall {
  call_id: string;
  freeswitch_uuid: string | null;
  caller_number: string | null;
  called_number: string | null;
  state: string;
  duration: number;
  message_count: number;
}

export interface CallMessage {
  id: number;
  role: string;
  content: string;
  audio_duration_ms: number | null;
  timestamp: string;
}

export interface Call {
  id: number;
  call_id: string;
  freeswitch_uuid: string | null;
  caller_number: string | null;
  called_number: string | null;
  prompt_id: number | null;
  status: string;
  direction: string;
  start_time: string;
  end_time: string | null;
  duration_seconds: number | null;
  summary: string | null;
  created_at: string;
  messages?: CallMessage[];
}

export interface CallsListResponse {
  items: Call[];
  total: number;
  page: number;
  per_page: number;
}

export interface Stats {
  total_calls: number;
  active_calls: number;
  completed_calls: number;
  avg_duration_seconds: number;
  max_concurrent_calls?: number;
}

export interface Setting {
  id: number;
  key: string;
  value: string;
  description: string | null;
  is_secret: boolean;
  is_configured: boolean;
  updated_at: string | null;
}

export interface TestApiKeyResponse {
  success: boolean;
  message: string;
}
