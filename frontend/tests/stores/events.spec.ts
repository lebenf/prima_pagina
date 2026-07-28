// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useEventsStore } from '@/stores/events'

vi.mock('@/api/events', () => ({
  eventsApi: {
    list: vi.fn(),
  },
}))

import { eventsApi } from '@/api/events'

function makeEvent(id: string) {
  return {
    id,
    title: `Event ${id}`,
    title_source: 'representative' as const,
    synopsis: null,
    tags: [],
    category_id: null,
    category_name: null,
    status: 'open' as const,
    article_count: 1,
    source_count: 1,
    opened_at: new Date().toISOString(),
    last_activity_at: new Date().toISOString(),
    user_vote: 0,
  }
}

describe('events store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('load populates events and pagination', async () => {
    vi.mocked(eventsApi.list).mockResolvedValueOnce({
      data: { items: [makeEvent('e1'), makeEvent('e2')], total: 2, page: 1, pages: 1 },
    } as any)

    const store = useEventsStore()
    await store.load()

    expect(store.events).toHaveLength(2)
    expect(store.pagination).toEqual({ total: 2, page: 1, pages: 1 })
    expect(store.isLoading).toBe(false)
  })

  it('load replaces existing events when append=false', async () => {
    const store = useEventsStore()
    store.events = [makeEvent('stale')] as any

    vi.mocked(eventsApi.list).mockResolvedValueOnce({
      data: { items: [makeEvent('fresh')], total: 1, page: 1, pages: 1 },
    } as any)
    await store.load()

    expect(store.events.map(e => e.id)).toEqual(['fresh'])
  })

  it('loadNextPage appends and requests the next page', async () => {
    const store = useEventsStore()
    vi.mocked(eventsApi.list).mockResolvedValueOnce({
      data: { items: [makeEvent('e1')], total: 3, page: 1, pages: 2 },
    } as any)
    await store.load()

    vi.mocked(eventsApi.list).mockResolvedValueOnce({
      data: { items: [makeEvent('e2')], total: 3, page: 2, pages: 2 },
    } as any)
    await store.loadNextPage()

    expect(eventsApi.list).toHaveBeenLastCalledWith({ page: 2, size: 20 })
    expect(store.events.map(e => e.id)).toEqual(['e1', 'e2'])
  })

  it('loadNextPage is a no-op when already on the last page', async () => {
    const store = useEventsStore()
    vi.mocked(eventsApi.list).mockResolvedValueOnce({
      data: { items: [makeEvent('e1')], total: 1, page: 1, pages: 1 },
    } as any)
    await store.load()

    vi.mocked(eventsApi.list).mockClear()
    await store.loadNextPage()

    expect(eventsApi.list).not.toHaveBeenCalled()
  })
})
