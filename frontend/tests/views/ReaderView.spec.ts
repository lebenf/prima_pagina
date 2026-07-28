// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import { setActivePinia, createPinia } from 'pinia'
import ReaderView from '@/views/ReaderView.vue'

vi.mock('@/api/feeds', () => ({
  feedsApi: {
    subscribed: vi.fn().mockResolvedValue({ data: [] }),
  },
}))

function makeArticle(id: string) {
  return {
    id, feed_id: 'f-1', feed_title: 'Feed', title: `Article ${id}`,
    url: null, author: null, content_excerpt: null, content_fulltext: null,
    fulltext_status: 'pending', fulltext_loading: false, fulltext_fetched_at: null,
    language: 'en', tags: [], published_at: new Date().toISOString(),
    fetched_at: new Date().toISOString(), is_read: false, is_starred: false,
    is_archived: false, user_vote: 0,
  }
}

vi.mock('@/api/articles', () => ({
  articlesApi: {
    list: vi.fn().mockResolvedValue({ data: { items: [], total: 0, page: 1, pages: 1, unread_count: 0 } }),
    get: vi.fn((id: string) => Promise.resolve({ data: makeArticle(id) })),
    updateState: vi.fn().mockResolvedValue({}),
  },
}))

import { articlesApi } from '@/api/articles'

async function makeWrapper(initialArticleId?: string) {
  setActivePinia(createPinia())
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/reader', name: 'reader', component: ReaderView },
    ],
  })
  router.push({ name: 'reader', query: initialArticleId ? { article: initialArticleId } : {} })
  await router.isReady()

  const wrapper = mount(ReaderView, {
    global: {
      plugins: [router],
      stubs: {
        FeedList: true,
        ArticleList: true,
        ArticleReader: true,
      },
    },
  })
  await flushPromises()
  return { wrapper, router }
}

describe('ReaderView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('loads the article from the initial ?article= query on mount', async () => {
    await makeWrapper('art-1')
    expect(articlesApi.get).toHaveBeenCalledWith('art-1')
  })

  it('does not fetch anything when there is no ?article= query', async () => {
    await makeWrapper()
    expect(articlesApi.get).not.toHaveBeenCalled()
  })

  it('regression: reacts to a SECOND ?article= navigation without unmounting (the reported blank-page bug)', async () => {
    const { router } = await makeWrapper('art-1')
    expect(articlesApi.get).toHaveBeenCalledWith('art-1')
    vi.mocked(articlesApi.get).mockClear()

    // Simulate a second SearchModal click while already inside /reader —
    // Vue Router reuses this component instance, onMounted does not re-fire.
    await router.push({ name: 'reader', query: { article: 'art-2' } })
    await flushPromises()

    expect(articlesApi.get).toHaveBeenCalledWith('art-2')
  })

  it('does not re-fetch the same article twice in a row', async () => {
    const { router } = await makeWrapper('art-1')
    vi.mocked(articlesApi.get).mockClear()

    await router.push({ name: 'reader', query: { article: 'art-1' } })
    await flushPromises()

    expect(articlesApi.get).not.toHaveBeenCalled()
  })
})
