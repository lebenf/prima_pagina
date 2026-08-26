// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
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
  confirm_password?: string
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
export interface ExtractionScript {
  feed_id: string
  selectors: Record<string, string>
  generated_at: string
  validated_at: string | null
  is_active: boolean
  success_rate: number
  consecutive_failures: number
  sample_url: string | null
}

export interface AdminFeed {
  id: string
  url: string
  title: string | null
  category_id: string | null
  fetch_interval_min: number
  source_weight: number
  is_active: boolean
  is_subscribed: boolean
  last_fetched_at: string | null
  last_status: number | null
  error_count: number
  fulltext_enabled: boolean
  fulltext_mode: string
  fulltext_include_images: boolean
  extraction_script: ExtractionScript | null
}

// ── Invitations ─────────────────────────────────────────────
export interface Invitation {
  id: string
  token: string
  email: string | null
  created_at: string
  expires_at: string
  used_at: string | null
  is_valid: boolean
  invite_url: string
}

export interface FeedCreate {
  url: string
  title?: string
  category_id?: string
  fetch_interval_min?: number
  source_weight?: number
  is_active?: boolean
  fulltext_enabled?: boolean
  fulltext_mode?: string
  fulltext_include_images?: boolean
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
  provider: 'ollama' | 'claude' | 'mistral' | 'hostyourai'
  label: string | null
  model_name: string
  endpoint_url: string | null
  has_api_key: boolean
  is_active: boolean
  timeout_sec: number
  max_concurrent: number
  tagging_language: string
  created_at: string
}

export interface LLMConfigCreate {
  provider: 'ollama' | 'claude' | 'mistral' | 'hostyourai'
  label?: string
  model_name: string
  endpoint_url?: string
  api_key?: string
  is_active: boolean
  timeout_sec: number
  max_concurrent: number
  tagging_language: string
}

// ── LLM Function Assignments ─────────────────────────────────
export type LLMFunctionName = 'tagging' | 'event_summary' | 'extraction_script' | 'related_articles' | 'digest'

export interface LLMFunctionAssignment {
  function: LLMFunctionName
  primary_config_id: string | null
  fallback_config_id: string | null
}

export interface LLMFunctionAssignmentUpdate {
  primary_config_id: string | null
  fallback_config_id: string | null
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
    revokeAllForUser: (userId: string) => client.delete(`/admin/sessions`, { data: { user_id: userId } }),
  },

  feeds: {
    list: () => client.get<{ items: AdminFeed[]; total: number; page: number; pages: number }>('/feeds', { params: { size: 200 } }),
    create: (data: FeedCreate) => client.post<AdminFeed>('/feeds', data),
    update: (id: string, data: Partial<FeedCreate>) => client.put<AdminFeed>(`/feeds/${id}`, data),
    delete: (id: string) => client.delete(`/feeds/${id}`),
    refresh: (id: string) => client.post(`/feeds/${id}/refresh`),
    discover: (url: string) => client.post<{ title: string; description: string | null }>('/feeds/discover', { url }),
  },

  categories: {
    list: () => client.get<AdminCategory[]>('/categories'),
    create: (data: CategoryCreate) => client.post<AdminCategory>('/categories', data),
    update: (id: string, data: CategoryCreate) => client.put<AdminCategory>(`/categories/${id}`, data),
    delete: (id: string) => client.delete(`/categories/${id}`),
  },

  llm: {
    list: () => client.get<LLMConfig[]>('/admin/llm-configs'),
    create: (data: LLMConfigCreate) => client.post<LLMConfig>('/admin/llm-configs', data),
    update: (id: string, data: Partial<LLMConfigCreate>) => client.put<LLMConfig>(`/admin/llm-configs/${id}`, data),
    delete: (id: string) => client.delete(`/admin/llm-configs/${id}`),
    healthCheck: (id: string) =>
      client.post<{ ok: boolean; latency_ms: number; error: string | null }>(`/admin/llm-configs/${id}/health-check`),
  },

  llmFunctions: {
    list: () => client.get<LLMFunctionAssignment[]>('/admin/llm-functions'),
    update: (fn: string, data: LLMFunctionAssignmentUpdate) =>
      client.put<LLMFunctionAssignment>(`/admin/llm-functions/${fn}`, data),
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

  invitations: {
    list: () => client.get<Invitation[]>('/admin/invitations'),
    create: (data: { email?: string; expires_days?: number }) =>
      client.post<Invitation>('/admin/invitations', data),
    revoke: (id: string) => client.delete(`/admin/invitations/${id}`),
  },

  events: {
    delete: (id: string) => client.delete(`/admin/events/${id}`),
  },

  extractionScript: {
    get: (feedId: string) => client.get<ExtractionScript>(`/feeds/${feedId}/extraction-script`),
    regenerate: (feedId: string) => client.post(`/feeds/${feedId}/extraction-script/regenerate`),
  },

  // ── Scheduler ─────────────────────────────────────────────────
  scheduler: {
    getSettings: () => client.get<TaskScheduleResponse>('/admin/scheduler/settings'),
    updateSettings: (data: TaskScheduleUpdate) => client.post<TaskScheduleResponse>('/admin/scheduler/settings', data),
    listTasks: () => client.get<ScheduledTaskResponse>('/admin/scheduler/tasks'),
    triggerFrontpageCache: () => client.post<{ message: string }>('/admin/scheduler/trigger-frontpage'),
    triggerDigestGeneration: () => client.post<{ message: string }>('/admin/scheduler/trigger-digest'),
  },
}

// Scheduler types
export interface ScheduledTaskInfo {
  id: string
  name: string
  trigger_type: string
  trigger_config: Record<string, any>
  next_run_time: string | null
}

export interface ScheduledTaskResponse {
  tasks: ScheduledTaskInfo[]
}

export interface TaskScheduleUpdate {
  digest_cron?: string
  frontpage_cron?: string
}

export interface TaskScheduleResponse {
  digest_cron: string
  frontpage_cron: string
  message: string
}
