// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { createRouter, createWebHistory } from 'vue-router'
import ArticleDrawer from '@/components/frontpage/ArticleDrawer.vue'
import en from '@/i18n/locales/en.json'

const mockArticle = {
  id: 'art-1',
  feed_id: 'f-1',
  feed_title: 'Test Feed',
  title: 'Test Article Title',
  url: 'https://example.com/article',
  author: 'Author Name',
  content_excerpt: '<p>Article excerpt text.</p>',
  content_fulltext: '<p>Full article text.</p>',
  fulltext_status: 'ok' as const,
  fulltext_loading: false,
  language: 'en',
  tags: ['tech', 'news'],
  published_at: '2026-04-22T10:00:00Z',
  fetched_at: '2026-04-22T10:30:00Z',
  is_read: false,
  is_starred: false,
  is_archived: false,
  user_vote: 0,
}

// Mock APIs — inline data (vi.mock is hoisted, cannot reference outer vars)
vi.mock('@/api/articles', () => ({
  articlesApi: {
    get: vi.fn().mockResolvedValue({
      data: {
        id: 'art-1', feed_id: 'f-1', feed_title: 'Test Feed',
        title: 'Test Article Title', url: 'https://example.com/article',
        author: 'Author Name', content_excerpt: '<p>Excerpt.</p>',
        content_fulltext: '<p>Full text.</p>', fulltext_status: 'ok',
        fulltext_loading: false, language: 'en', tags: ['tech'],
        published_at: '2026-04-22T10:00:00Z', fetched_at: '2026-04-22T10:30:00Z',
        is_read: false, is_starred: false, is_archived: false, user_vote: 0,
      },
    }),
    fulltextStatus: vi.fn().mockResolvedValue({ data: { status: 'ok', fulltext_available: false } }),
    updateState: vi.fn().mockResolvedValue({}),
    vote: vi.fn().mockResolvedValue({}),
    removeVote: vi.fn().mockResolvedValue({}),
    related: vi.fn().mockResolvedValue({ data: [] }),
  },
}))

// Stub child components that make API calls
const RelatedArticlesStub = { template: '<div class="related-articles-stub"></div>', props: ['articleId'] }
const LoadingSpinnerStub = { template: '<div class="spinner-stub"></div>' }
const RelativeTimeStub = { template: '<span class="relative-time-stub"></span>', props: ['date'] }
const VoteButtonsStub = { template: '<div class="vote-buttons-stub"></div>', props: ['articleId', 'initialVote', 'compact'] }

function makeWrapper(articleId: string | null = null) {
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/reader', name: 'reader', component: { template: '<div />' } },
    ],
  })
  return mount(ArticleDrawer, {
    props: { articleId },
    global: {
      plugins: [i18n, router],
      stubs: {
        RelatedArticles: RelatedArticlesStub,
        LoadingSpinner: LoadingSpinnerStub,
        RelativeTime: RelativeTimeStub,
        VoteButtons: VoteButtonsStub,
        RouterLink: { template: '<a><slot /></a>' },
        Teleport: { template: '<div><slot /></div>' },
        Transition: { template: '<slot />' },
      },
    },
    attachTo: document.body,
  })
}

describe('ArticleDrawer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    document.body.style.overflow = ''
  })

  it('is not visible when articleId is null', async () => {
    const wrapper = makeWrapper(null)
    expect(wrapper.find('.drawer-overlay').exists()).toBe(false)
  })

  it('opens when articleId is set', async () => {
    const wrapper = makeWrapper('art-1')
    await new Promise(r => setTimeout(r, 20))
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.drawer-panel').exists()).toBe(true)
  })

  it('loads article content on open', async () => {
    const { articlesApi } = await import('@/api/articles')
    makeWrapper('art-1')
    await new Promise(r => setTimeout(r, 20))
    expect(articlesApi.get).toHaveBeenCalledWith('art-1')
  })

  it('emits close event on X button click', async () => {
    const wrapper = makeWrapper('art-1')
    await new Promise(r => setTimeout(r, 20))
    await wrapper.vm.$nextTick()
    const closeBtn = wrapper.find('.drawer-close')
    await closeBtn.trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('emits close on overlay click', async () => {
    const wrapper = makeWrapper('art-1')
    await new Promise(r => setTimeout(r, 20))
    await wrapper.vm.$nextTick()
    const overlay = wrapper.find('.drawer-overlay')
    await overlay.trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('locks body scroll when open', async () => {
    makeWrapper('art-1')
    await new Promise(r => setTimeout(r, 20))
    expect(document.body.style.overflow).toBe('hidden')
  })

  it('restores body scroll on unmount', async () => {
    const wrapper = makeWrapper('art-1')
    await new Promise(r => setTimeout(r, 20))
    wrapper.unmount()
    expect(document.body.style.overflow).toBe('')
  })

  it('renders related articles section', async () => {
    const wrapper = makeWrapper('art-1')
    await new Promise(r => setTimeout(r, 20))
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.related-articles-stub').exists()).toBe(true)
  })

  it('renders article title', async () => {
    const wrapper = makeWrapper('art-1')
    await new Promise(r => setTimeout(r, 20))
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.article-title').text()).toContain('Test Article Title')
  })

  it('does not call API when articleId is null', async () => {
    const { articlesApi } = await import('@/api/articles')
    makeWrapper(null)
    await new Promise(r => setTimeout(r, 20))
    expect(articlesApi.get).not.toHaveBeenCalled()
  })
})
