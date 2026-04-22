import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useFrontPageStore } from '@/stores/frontpage'

vi.mock('@/api/articles', () => ({
  articlesApi: {
    frontpage: vi.fn(),
    updateState: vi.fn(),
  },
}))

vi.mock('@/api/digest', () => ({
  digestApi: {
    get: vi.fn(),
    generate: vi.fn(),
  },
}))

import { articlesApi } from '@/api/articles'
import { digestApi } from '@/api/digest'

const mockFrontPageData = {
  hero: { id: 'a1', title: 'Hero Article', feed_title: 'Feed A', tags: ['politics'], published_at: new Date().toISOString(), fetched_at: new Date().toISOString(), feed_id: 'f1', url: null, author: null, content_excerpt: null, content_fulltext: null, fulltext_status: 'pending', fulltext_loading: false, language: null, is_read: false, is_starred: false, is_archived: false },
  second_row: [],
  columns: [],
  digest_available: false,
  digest_id: null,
}

const mockDigest = {
  id: 'd1',
  title: 'Test Digest',
  period_start: '2026-04-21T00:00:00',
  period_end: '2026-04-22T00:00:00',
  content_html: '<h2>News</h2><p>Summary</p>',
  content_text: 'News\nSummary',
  virtual_feed_id: null,
  llm_provider: 'claude',
  llm_model: 'claude-opus-4-7',
  article_count: 5,
  created_at: new Date().toISOString(),
}

describe('frontpage store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('load populates data', async () => {
    vi.mocked(articlesApi.frontpage).mockResolvedValueOnce({ data: mockFrontPageData } as any)

    const store = useFrontPageStore()
    await store.load('it')

    expect(store.data).toBeTruthy()
    expect(store.data?.hero?.id).toBe('a1')
    expect(store.lastUpdated).toBeInstanceOf(Date)
    expect(store.isLoading).toBe(false)
  })

  it('load fetches digest when digest_available', async () => {
    const dataWithDigest = { ...mockFrontPageData, digest_available: true, digest_id: 'd1' }
    vi.mocked(articlesApi.frontpage).mockResolvedValueOnce({ data: dataWithDigest } as any)
    vi.mocked(digestApi.get).mockResolvedValueOnce({ data: mockDigest } as any)

    const store = useFrontPageStore()
    await store.load('it')

    expect(digestApi.get).toHaveBeenCalledWith('d1')
    expect(store.digest?.id).toBe('d1')
  })

  it('load sets error on failure', async () => {
    vi.mocked(articlesApi.frontpage).mockRejectedValueOnce({ response: { data: { detail: 'Server error' } } })

    const store = useFrontPageStore()
    await store.load('it')

    expect(store.error).toBe('Server error')
    expect(store.data).toBeNull()
  })

  it('generateDigest updates digest and shows banner', async () => {
    vi.mocked(digestApi.generate).mockResolvedValueOnce({ data: mockDigest } as any)

    const store = useFrontPageStore()
    store.data = { ...mockFrontPageData }
    store.digestDismissed = true

    await store.generateDigest()

    expect(store.digest?.id).toBe('d1')
    expect(store.digestDismissed).toBe(false)
    expect(store.isGeneratingDigest).toBe(false)
    expect(store.data?.digest_available).toBe(true)
  })

  it('dismissDigest hides banner', () => {
    const store = useFrontPageStore()
    store.digest = mockDigest as any

    expect(store.showDigest).toBe(true)
    store.dismissDigest()
    expect(store.showDigest).toBe(false)
    expect(store.digestDismissed).toBe(true)
  })

  it('showDigest is false when digest is null', () => {
    const store = useFrontPageStore()
    expect(store.showDigest).toBe(false)
  })

  it('showDigest is false when dismissed', () => {
    const store = useFrontPageStore()
    store.digest = mockDigest as any
    store.digestDismissed = true
    expect(store.showDigest).toBe(false)
  })

  it('autoRefresh starts and stops', () => {
    vi.useFakeTimers()
    vi.mocked(articlesApi.frontpage).mockResolvedValue({ data: mockFrontPageData } as any)

    const store = useFrontPageStore()
    store.startAutoRefresh()

    vi.advanceTimersByTime(10 * 60 * 1000)
    expect(articlesApi.frontpage).toHaveBeenCalled()

    store.stopAutoRefresh()
    const callCount = vi.mocked(articlesApi.frontpage).mock.calls.length
    vi.advanceTimersByTime(10 * 60 * 1000)
    expect(vi.mocked(articlesApi.frontpage).mock.calls.length).toBe(callCount)

    vi.useRealTimers()
  })
})
