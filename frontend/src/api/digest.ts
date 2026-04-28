// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import client from './client'

export interface Digest {
  id: string
  title: string | null
  period_start: string
  period_end: string
  content_html: string | null
  content_text: string | null
  virtual_feed_id: string | null
  llm_provider: string | null
  llm_model: string | null
  article_count: number
  status: string
  generation_error: string | null
  created_at: string
}

export interface DigestGenerateOptions {
  period_start?: string
  period_end?: string
  virtual_feed_id?: string
  category_ids?: string[]
  max_articles?: number
  force_fulltext?: boolean
}

export const digestApi = {
  list: (params?: { page?: number; size?: number; virtual_feed_id?: string }) =>
    client.get<{ items: Digest[]; total: number; page: number; pages: number }>('/digests', { params }),

  get: (id: string) =>
    client.get<Digest>(`/digests/${id}`),

  latest: (virtualFeedId?: string) =>
    client.get<Digest>('/digests/latest', {
      params: virtualFeedId ? { virtual_feed_id: virtualFeedId } : {},
    }),

  generate: (options: DigestGenerateOptions = {}) =>
    client.post<Digest>('/digests/generate', options),

  delete: (id: string) =>
    client.delete(`/digests/${id}`),
}
