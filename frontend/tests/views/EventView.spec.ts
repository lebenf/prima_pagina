// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { createRouter, createWebHistory } from 'vue-router'
import EventView from '@/views/EventView.vue'
import en from '@/i18n/locales/en.json'

vi.mock('@/api/events', () => ({
  eventsApi: {
    get: vi.fn(),
    vote: vi.fn().mockResolvedValue({}),
    removeVote: vi.fn().mockResolvedValue({}),
  },
}))

vi.mock('@/api/articles', () => ({
  articlesApi: {
    updateState: vi.fn().mockResolvedValue({}),
  },
}))

import { eventsApi } from '@/api/events'

const mockEventDetail = {
  id: 'evt-1',
  title: 'Major event unfolds',
  title_source: 'llm' as const,
  synopsis: 'A concise synopsis.',
  tags: ['politics'],
  category_id: 'cat-1',
  category_name: 'Politics',
  status: 'open' as const,
  article_count: 2,
  source_count: 2,
  opened_at: new Date().toISOString(),
  last_activity_at: new Date().toISOString(),
  user_vote: 0,
  articles: [
    {
      id: 'art-1', feed_id: 'f-1', feed_title: 'Feed A', title: 'Article One',
      url: 'https://a.example.com/1', author: null, content_excerpt: null,
      content_fulltext: null, fulltext_status: 'pending', fulltext_loading: false,
      fulltext_fetched_at: null, language: 'en', tags: ['politics'],
      published_at: new Date().toISOString(), fetched_at: new Date().toISOString(),
      is_read: false, is_starred: false, is_archived: false, user_vote: 0,
    },
    {
      id: 'art-2', feed_id: 'f-2', feed_title: 'Feed B', title: 'Article Two',
      url: 'https://b.example.com/2', author: null, content_excerpt: null,
      content_fulltext: null, fulltext_status: 'pending', fulltext_loading: false,
      fulltext_fetched_at: null, language: 'en', tags: ['politics'],
      published_at: new Date().toISOString(), fetched_at: new Date().toISOString(),
      is_read: false, is_starred: false, is_archived: false, user_vote: 0,
    },
  ],
}

async function makeWrapper() {
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/events/:id', name: 'event', component: EventView },
      { path: '/reader', name: 'reader', component: { template: '<div />' } },
    ],
  })
  router.push('/events/evt-1')
  await router.isReady()

  return mount(EventView, {
    global: { plugins: [i18n, router] },
  })
}

describe('EventView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(eventsApi.get).mockResolvedValue({ data: mockEventDetail } as any)
  })

  it('fetches the event on mount', async () => {
    await makeWrapper()
    await flushPromises()
    expect(eventsApi.get).toHaveBeenCalledWith('evt-1')
  })

  it('shows a loading spinner before data arrives', async () => {
    let resolve!: (v: any) => void
    vi.mocked(eventsApi.get).mockReturnValueOnce(new Promise(r => { resolve = r }) as any)

    const wrapper = await makeWrapper()
    expect(wrapper.find('.event-view').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('Major event unfolds')

    resolve({ data: mockEventDetail })
    await flushPromises()
    expect(wrapper.text()).toContain('Major event unfolds')
  })

  it('renders hero title and synopsis', async () => {
    const wrapper = await makeWrapper()
    await flushPromises()
    expect(wrapper.text()).toContain('Major event unfolds')
    expect(wrapper.text()).toContain('A concise synopsis.')
  })

  it('renders the member article list grouped by source', async () => {
    const wrapper = await makeWrapper()
    await flushPromises()
    const members = wrapper.findAll('.event-member')
    expect(members).toHaveLength(2)
    expect(members[0].text()).toContain('Feed A')
    expect(members[0].text()).toContain('Article One')
    expect(members[1].text()).toContain('Feed B')
    expect(members[1].text()).toContain('Article Two')
  })

  it('marking an article read calls articlesApi.updateState', async () => {
    const { articlesApi } = await import('@/api/articles')
    const wrapper = await makeWrapper()
    await flushPromises()

    const markReadBtn = wrapper.findAll('.event-member')[0].findAll('button')
      .find(b => b.text().toLowerCase().includes('read'))
    await markReadBtn!.trigger('click')

    expect(articlesApi.updateState).toHaveBeenCalledWith('art-1', { is_read: true })
  })
})
