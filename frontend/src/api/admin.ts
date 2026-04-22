import client from './client'

// ── Users ──────────────────────────────────────────────────
export interface AdminUser {
  id: string
  email: string
  username: string
  preferred_lang: string
  role: 'admin' | 'user'
  is_active: boolean
  created_at: string
}

export interface UserCreate {
  email: string
  username: string
  password: string
  role: 'admin' | 'user'
  preferred_lang: string
}

export interface UserUpdate {
  email?: string
  username?: string
  password?: string
  role?: 'admin' | 'user'
  is_active?: boolean
  preferred_lang?: string
}

// ── Sessions ────────────────────────────────────────────────
export interface AdminSession {
  id: string
  user_id: string
  username: string
  created_at: string
  expires_at: string
  last_active_at: string
  ip_address: string | null
  user_agent: string | null
  is_revoked: boolean
}

// ── Feeds ───────────────────────────────────────────────────
export interface AdminFeed {
  id: string
  url: string
  title: string
  category_id: string | null
  category_name: string | null
  fetch_interval_min: number
  source_weight: number
  is_active: boolean
  last_fetched_at: string | null
  last_http_status: number | null
  error_count: number
}

export interface FeedCreate {
  url: string
  title?: string
  category_id?: string
  fetch_interval_min?: number
  source_weight?: number
  is_active?: boolean
}

// ── Categories ──────────────────────────────────────────────
export interface AdminCategory {
  id: string
  slug: string
  name: Record<string, string>
  feed_count?: number
}

export interface CategoryCreate {
  slug: string
  name: Record<string, string>
}

// ── LLM Config ──────────────────────────────────────────────
export interface LLMConfig {
  id: string
  provider: 'ollama' | 'claude'
  label: string | null
  model_name: string
  endpoint_url: string | null
  has_api_key: boolean
  use_for: string[]
  is_default: boolean
  is_active: boolean
  priority: number
  created_at: string
}

export interface LLMConfigCreate {
  provider: 'ollama' | 'claude'
  label?: string
  model_name: string
  endpoint_url?: string
  api_key?: string
  use_for: string[]
  is_default: boolean
  is_active: boolean
  priority: number
}

// ── Plugin ──────────────────────────────────────────────────
export interface PluginConfig {
  id: string
  plugin_type: string
  label: string | null
  user_id: string | null
  is_active: boolean
  has_config: boolean
  created_at: string
}

export interface PluginAvailable {
  plugin_type: string
  label: string
  description: string
  config_schema: Record<string, {
    type: string
    required: boolean
    secret: boolean
    label: string
    default?: any
    description?: string
  }>
}

export const adminApi = {
  users: {
    list: () => client.get<AdminUser[]>('/admin/users'),
    create: (data: UserCreate) => client.post<AdminUser>('/admin/users', data),
    update: (id: string, data: UserUpdate) => client.put<AdminUser>(`/admin/users/${id}`, data),
    delete: (id: string) => client.delete(`/admin/users/${id}`),
  },

  sessions: {
    list: () => client.get<AdminSession[]>('/admin/sessions'),
    revoke: (id: string) => client.delete(`/admin/sessions/${id}`),
    revokeAllForUser: (userId: string) => client.delete(`/admin/sessions/user/${userId}`),
  },

  feeds: {
    list: () => client.get<AdminFeed[]>('/admin/feeds'),
    create: (data: FeedCreate) => client.post<AdminFeed>('/admin/feeds', data),
    update: (id: string, data: Partial<FeedCreate>) => client.put<AdminFeed>(`/admin/feeds/${id}`, data),
    delete: (id: string) => client.delete(`/admin/feeds/${id}`),
    refresh: (id: string) => client.post(`/feeds/${id}/refresh`),
    discover: (url: string) => client.post<{ title: string; description: string | null }>('/feeds/discover', { url }),
  },

  categories: {
    list: () => client.get<AdminCategory[]>('/categories'),
    create: (data: CategoryCreate) => client.post<AdminCategory>('/admin/categories', data),
    update: (id: string, data: CategoryCreate) => client.put<AdminCategory>(`/admin/categories/${id}`, data),
    delete: (id: string) => client.delete(`/admin/categories/${id}`),
  },

  llm: {
    list: () => client.get<LLMConfig[]>('/admin/llm-configs'),
    create: (data: LLMConfigCreate) => client.post<LLMConfig>('/admin/llm-configs', data),
    update: (id: string, data: Partial<LLMConfigCreate>) => client.put<LLMConfig>(`/admin/llm-configs/${id}`, data),
    delete: (id: string) => client.delete(`/admin/llm-configs/${id}`),
    healthCheck: (id: string) =>
      client.post<{ ok: boolean; latency_ms: number; error: string | null }>(`/admin/llm-configs/${id}/health-check`),
  },

  plugins: {
    list: () => client.get<PluginConfig[]>('/admin/plugins'),
    available: () => client.get<PluginAvailable[]>('/admin/plugins/available'),
    create: (data: { plugin_type: string; label?: string; config_json: Record<string, any>; user_id?: string; is_active: boolean }) =>
      client.post<PluginConfig>('/admin/plugins', data),
    update: (id: string, data: any) => client.put<PluginConfig>(`/admin/plugins/${id}`, data),
    delete: (id: string) => client.delete(`/admin/plugins/${id}`),
    test: (id: string) =>
      client.post<{ ok: boolean; message: string; latency_ms: number }>(`/admin/plugins/${id}/test`),
  },
}
