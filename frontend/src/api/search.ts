// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import client from './client'

export interface SearchResult {
  id: string
  feed_id: string
  feed_title: string | null
  title: string | null
  title_highlighted: string | null
  excerpt_snippet: string | null
  url: string | null
  published_at: string | null
  language: string | null
  tags: string[]
  is_read: boolean
  is_starred: boolean
  user_vote: number
}

export interface SearchResponse {
  items: SearchResult[]
  total: number
  page: number
  pages: number
  query: string
}

export const searchApi = {
  search: (params: {
    q: string
    feed_id?: string
    category_id?: string
    date_from?: string
    date_to?: string
    page?: number
    size?: number
  }) => client.get<SearchResponse>('/search', { params }),
}
