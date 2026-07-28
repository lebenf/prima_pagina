// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { createRouter, createWebHistory } from 'vue-router'
import { setActivePinia, createPinia } from 'pinia'
import EventsView from '@/views/EventsView.vue'
import en from '@/i18n/locales/en.json'

vi.mock('@/api/events', () => ({
  eventsApi: {
    list: vi.fn(),
    vote: vi.fn().mockResolvedValue({}),
    removeVote: vi.fn().mockResolvedValue({}),
  },
}))

import { eventsApi } from '@/api/events'

function makeEvent(id: string, title: string) {
  return {
    id,
    title,
    title_source: 'representative' as const,
    synopsis: 'Synopsis text',
    tags: ['tech'],
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

async function makeWrapper() {
  setActivePinia(createPinia())
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', name: 'events', component: EventsView },
      { path: '/events/:id', name: 'event', component: { template: '<div />' } },
    ],
  })
  router.push('/')
  await router.isReady()

  return mount(EventsView, {
    global: {
      plugins: [i18n, router],
      stubs: { InfiniteScroll: true },
    },
  })
}

describe('EventsView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetches events on mount', async () => {
    vi.mocked(eventsApi.list).mockResolvedValueOnce({
      data: { items: [], total: 0, page: 1, pages: 1 },
    } as any)
    await makeWrapper()
    await flushPromises()
    expect(eventsApi.list).toHaveBeenCalled()
  })

  it('shows the empty state when there are no events', async () => {
    vi.mocked(eventsApi.list).mockResolvedValueOnce({
      data: { items: [], total: 0, page: 1, pages: 1 },
    } as any)
    const wrapper = await makeWrapper()
    await flushPromises()
    expect(wrapper.text()).toContain('No events detected')
  })

  it('renders events in the order returned by the API', async () => {
    vi.mocked(eventsApi.list).mockResolvedValueOnce({
      data: {
        items: [makeEvent('e1', 'Newest event'), makeEvent('e2', 'Older event')],
        total: 2, page: 1, pages: 1,
      },
    } as any)
    const wrapper = await makeWrapper()
    await flushPromises()

    const items = wrapper.findAll('.events-view__list li')
    expect(items).toHaveLength(2)
    expect(items[0].text()).toContain('Newest event')
    expect(items[1].text()).toContain('Older event')
  })

  it('navigates to the event detail route on card click', async () => {
    vi.mocked(eventsApi.list).mockResolvedValueOnce({
      data: { items: [makeEvent('e1', 'Some event')], total: 1, page: 1, pages: 1 },
    } as any)
    const wrapper = await makeWrapper()
    await flushPromises()

    await wrapper.find('.event-card').trigger('click')
    await flushPromises()

    expect(wrapper.vm.$route.fullPath).toBe('/events/e1')
  })
})
