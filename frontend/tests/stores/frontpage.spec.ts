// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useFrontPageStore } from '@/stores/frontpage'

vi.mock('@/api/events', () => ({
  eventsApi: {
    frontpage: vi.fn(),
  },
}))

vi.mock('@/api/digest', () => ({
  digestApi: {
    get: vi.fn(),
    generate: vi.fn(),
  },
}))

import { eventsApi } from '@/api/events'
import { digestApi } from '@/api/digest'

const mockFrontPageData = {
  hero: {
    id: 'e1', title: 'Hero Event', title_source: 'representative' as const,
    synopsis: 'Synopsis text', tags: ['politics'], category_id: null, category_name: null,
    status: 'open' as const, article_count: 1, source_count: 1,
    opened_at: new Date().toISOString(), last_activity_at: new Date().toISOString(),
    user_vote: 0,
  },
  second_row: [],
  columns: [],
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
    vi.mocked(eventsApi.frontpage).mockResolvedValueOnce({ data: mockFrontPageData } as any)

    const store = useFrontPageStore()
    await store.load('it')

    expect(store.data).toBeTruthy()
    expect(store.data?.hero?.id).toBe('e1')
    expect(store.lastUpdated).toBeInstanceOf(Date)
    expect(store.isLoading).toBe(false)
  })

  it('load sets error on failure', async () => {
    vi.mocked(eventsApi.frontpage).mockRejectedValueOnce({ response: { data: { detail: 'Server error' } } })

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
    vi.mocked(eventsApi.frontpage).mockResolvedValue({ data: mockFrontPageData } as any)

    const store = useFrontPageStore()
    store.startAutoRefresh()

    vi.advanceTimersByTime(10 * 60 * 1000)
    expect(eventsApi.frontpage).toHaveBeenCalled()

    store.stopAutoRefresh()
    const callCount = vi.mocked(eventsApi.frontpage).mock.calls.length
    vi.advanceTimersByTime(10 * 60 * 1000)
    expect(vi.mocked(eventsApi.frontpage).mock.calls.length).toBe(callCount)

    vi.useRealTimers()
  })
})
