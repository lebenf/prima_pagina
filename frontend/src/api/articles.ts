import client from './client'

export interface Article {
  id: string
  feed_id: string
  feed_title: string | null
  title: string | null
  url: string | null
  author: string | null
  content_excerpt: string | null
  content_fulltext: string | null
  fulltext_status: 'pending' | 'ok' | 'failed' | 'blocked'
  fulltext_loading: boolean
  language: string | null
  tags: string[]
  published_at: string | null
  fetched_at: string
  is_read: boolean
  is_starred: boolean
  is_archived: boolean
}

export interface ArticleListResponse {
  items: Article[]
  total: number
  page: number
  pages: number
  unread_count: number
}

export interface ArticleFilters {
  feed_id?: string
  category_id?: string
  tags?: string[]
  is_read?: boolean
  is_starred?: boolean
  is_archived?: boolean
  search?: string
  page?: number
  size?: number
  order_by?: 'published_at' | 'fetched_at'
  order_dir?: 'asc' | 'desc'
}

export const articlesApi = {
  list: (filters: ArticleFilters = {}) =>
    client.get<ArticleListResponse>('/articles', { params: filters }),

  get: (id: string) =>
    client.get<Article>(`/articles/${id}`),

  fulltextStatus: (id: string) =>
    client.get<{ status: string; fulltext_available: boolean }>(`/articles/${id}/fulltext-status`),

  updateState: (id: string, state: { is_read?: boolean; is_starred?: boolean; is_archived?: boolean }) =>
    client.patch(`/articles/${id}/state`, state),

  markFeedRead: (feedId: string, before?: string) =>
    client.post('/articles/mark-read', { feed_id: feedId, before }),

  frontpage: (lang?: string) =>
    client.get('/articles/frontpage', { params: { lang } }),
}
