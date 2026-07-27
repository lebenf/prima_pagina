// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import client from './client'
import type { Article } from './articles'

export interface Event {
  id: string
  title: string
  title_source: 'representative' | 'llm'
  synopsis: string | null
  tags: string[]
  category_id: string | null
  category_name: string | null
  status: 'open' | 'closed'
  article_count: number
  source_count: number
  opened_at: string
  last_activity_at: string
  user_vote: number
}

export interface EventDetail extends Event {
  articles: Article[]
}

export interface EventFrontPageColumn {
  category_slug: string
  category_name: string
  events: Event[]
}

export interface EventFrontPageResponse {
  hero: Event | null
  second_row: Event[]
  columns: EventFrontPageColumn[]
  digest_available: boolean
  digest_id: string | null
}

export const eventsApi = {
  frontpage: (lang?: string) =>
    client.get<EventFrontPageResponse>('/events/frontpage', { params: { lang } }),

  get: (id: string) =>
    client.get<EventDetail>(`/events/${id}`),

  vote: (id: string, vote: 1 | -1) =>
    client.post(`/events/${id}/vote`, { vote }),

  removeVote: (id: string) =>
    client.delete(`/events/${id}/vote`),
}
