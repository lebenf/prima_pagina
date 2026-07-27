// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import EventCard from '@/components/frontpage/EventCard.vue'
import en from '@/i18n/locales/en.json'

vi.mock('@/api/events', () => ({
  eventsApi: {
    vote: vi.fn().mockResolvedValue({}),
    removeVote: vi.fn().mockResolvedValue({}),
  },
}))

import { eventsApi } from '@/api/events'

const baseEvent = {
  id: 'evt-1',
  title: 'Major event unfolds',
  title_source: 'llm' as const,
  synopsis: 'A concise synopsis of the event.',
  tags: ['politics', 'world'],
  category_id: 'cat-1',
  category_name: 'Politics',
  status: 'open' as const,
  article_count: 3,
  source_count: 1,
  opened_at: new Date().toISOString(),
  last_activity_at: new Date().toISOString(),
  user_vote: 0,
}

function makeWrapper(props: Record<string, any> = {}) {
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  return mount(EventCard, {
    props: { event: baseEvent, size: 'row', ...props },
    global: {
      plugins: [i18n],
      stubs: { RelativeTime: { template: '<span />' } },
    },
  })
}

describe('EventCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders title and synopsis for size=hero', () => {
    const wrapper = makeWrapper({ size: 'hero' })
    expect(wrapper.text()).toContain('Major event unfolds')
    expect(wrapper.text()).toContain('A concise synopsis of the event.')
  })

  it('renders title and synopsis for size=row', () => {
    const wrapper = makeWrapper({ size: 'row' })
    expect(wrapper.text()).toContain('Major event unfolds')
    expect(wrapper.text()).toContain('A concise synopsis of the event.')
  })

  it('size=compact renders title but not synopsis', () => {
    const wrapper = makeWrapper({ size: 'compact' })
    expect(wrapper.text()).toContain('Major event unfolds')
    expect(wrapper.text()).not.toContain('A concise synopsis of the event.')
  })

  it('shows the multi-source badge when source_count > 1', () => {
    const wrapper = makeWrapper({ event: { ...baseEvent, source_count: 3 } })
    expect(wrapper.text()).toContain('3 sources')
  })

  it('hides the multi-source badge when source_count is 1', () => {
    const wrapper = makeWrapper({ event: { ...baseEvent, source_count: 1 } })
    expect(wrapper.text()).not.toContain('sources')
  })

  it('emits click when clicked', async () => {
    const wrapper = makeWrapper()
    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toBeTruthy()
  })

  it('casting a vote calls eventsApi.vote (not articlesApi)', async () => {
    const wrapper = makeWrapper()
    const upButton = wrapper.findAll('button').find(b => b.text().includes('👍'))
    await upButton!.trigger('click')
    expect(eventsApi.vote).toHaveBeenCalledWith('evt-1', 1)
  })

  it('clicking the vote button does not also trigger the card click (stopPropagation)', async () => {
    const wrapper = makeWrapper()
    const upButton = wrapper.findAll('button').find(b => b.text().includes('👍'))
    await upButton!.trigger('click')
    expect(wrapper.emitted('click')).toBeFalsy()
  })
})
