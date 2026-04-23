// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import client from './client'

export interface Feed {
  id: string
  title: string | null
  site_url: string | null
  favicon_url: string | null
  category_id: string | null
  language: string | null
  last_fetched_at: string | null
  is_active: boolean
  is_subscribed: boolean
  custom_name?: string
}

export const feedsApi = {
  list: (params?: { category_id?: string; subscribed?: boolean }) =>
    client.get<{ items: Feed[]; total: number }>('/feeds', { params }),

  subscribed: () =>
    client.get<Feed[]>('/feeds/subscribed'),

  subscribe: (feedId: string, data?: { custom_name?: string; notify_on_new?: boolean }) =>
    client.post(`/feeds/${feedId}/subscribe`, data),

  unsubscribe: (feedId: string) =>
    client.delete(`/feeds/${feedId}/subscribe`),

  get: (feedId: string) =>
    client.get<Feed>(`/feeds/${feedId}`),
}
