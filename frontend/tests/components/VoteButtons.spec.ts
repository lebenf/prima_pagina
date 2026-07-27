// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import VoteButtons from '@/components/common/VoteButtons.vue'
import en from '@/i18n/locales/en.json'

// Mock both APIs
vi.mock('@/api/articles', () => ({
  articlesApi: {
    vote: vi.fn().mockResolvedValue({}),
    removeVote: vi.fn().mockResolvedValue({}),
  },
}))

vi.mock('@/api/events', () => ({
  eventsApi: {
    vote: vi.fn().mockResolvedValue({}),
    removeVote: vi.fn().mockResolvedValue({}),
  },
}))

import { articlesApi } from '@/api/articles'
import { eventsApi } from '@/api/events'

function makeWrapper(props = {}) {
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  return mount(VoteButtons, {
    props: { targetId: 'art-1', initialVote: 0, compact: false, ...props },
    global: { plugins: [i18n] },
  })
}

describe('VoteButtons', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders thumbs up and down buttons', () => {
    const wrapper = makeWrapper()
    const buttons = wrapper.findAll('button')
    expect(buttons).toHaveLength(2)
    expect(buttons[0].text()).toContain('👍')
    expect(buttons[1].text()).toContain('👎')
  })

  it('shows no active state when vote is 0', () => {
    const wrapper = makeWrapper({ initialVote: 0 })
    const buttons = wrapper.findAll('button')
    expect(buttons[0].classes()).not.toContain('active')
    expect(buttons[1].classes()).not.toContain('active')
  })

  it('highlights active vote up', () => {
    const wrapper = makeWrapper({ initialVote: 1 })
    const upBtn = wrapper.findAll('button')[0]
    expect(upBtn.classes()).toContain('active')
  })

  it('highlights active vote down', () => {
    const wrapper = makeWrapper({ initialVote: -1 })
    const downBtn = wrapper.findAll('button')[1]
    expect(downBtn.classes()).toContain('active')
  })

  it('defaults to target=article and calls articlesApi', async () => {
    const wrapper = makeWrapper({ initialVote: 0 })
    await wrapper.findAll('button')[0].trigger('click')
    expect(articlesApi.vote).toHaveBeenCalledWith('art-1', 1)
    expect(eventsApi.vote).not.toHaveBeenCalled()
  })

  it('calls vote API on thumbs-up click', async () => {
    const wrapper = makeWrapper({ initialVote: 0 })
    await wrapper.findAll('button')[0].trigger('click')
    expect(articlesApi.vote).toHaveBeenCalledWith('art-1', 1)
  })

  it('calls vote API on thumbs-down click', async () => {
    const wrapper = makeWrapper({ initialVote: 0 })
    await wrapper.findAll('button')[1].trigger('click')
    expect(articlesApi.vote).toHaveBeenCalledWith('art-1', -1)
  })

  it('calls removeVote on second click (toggle off)', async () => {
    const wrapper = makeWrapper({ initialVote: 1 })
    await wrapper.findAll('button')[0].trigger('click')
    expect(articlesApi.removeVote).toHaveBeenCalledWith('art-1')
  })

  it('emits vote-changed after vote', async () => {
    const wrapper = makeWrapper({ initialVote: 0 })
    await wrapper.findAll('button')[0].trigger('click')
    // wait for async
    await new Promise(r => setTimeout(r, 10))
    expect(wrapper.emitted('vote-changed')).toBeTruthy()
    expect(wrapper.emitted('vote-changed')![0]).toEqual([1, 'art-1'])
  })

  it('emits vote-changed with 0 on toggle off', async () => {
    const wrapper = makeWrapper({ initialVote: 1 })
    await wrapper.findAll('button')[0].trigger('click')
    await new Promise(r => setTimeout(r, 10))
    expect(wrapper.emitted('vote-changed')![0]).toEqual([0, 'art-1'])
  })

  it('rollbacks vote on API error', async () => {
    vi.mocked(articlesApi.vote).mockRejectedValueOnce(new Error('fail'))
    const wrapper = makeWrapper({ initialVote: 0 })
    await wrapper.findAll('button')[0].trigger('click')
    await new Promise(r => setTimeout(r, 10))
    // Should rollback to 0
    expect(wrapper.findAll('button')[0].classes()).not.toContain('active')
  })

  it('compact mode hides labels', () => {
    const wrapper = makeWrapper({ compact: true })
    expect(wrapper.find('.vote-label').exists()).toBe(false)
  })

  it('non-compact mode shows labels', () => {
    const wrapper = makeWrapper({ compact: false })
    expect(wrapper.find('.vote-label').exists()).toBe(true)
  })

  it('click stops propagation', async () => {
    const wrapper = makeWrapper()
    const btn = wrapper.findAll('button')[0]
    const clickEvent = new MouseEvent('click', { bubbles: true })
    btn.element.dispatchEvent(clickEvent)
    // @click.stop means stopPropagation is called by Vue, test passes if no parent handler called
    expect(wrapper.emitted('click')).toBeFalsy()
  })

  // ---------------------------------------------------------------------
  // target="event"
  // ---------------------------------------------------------------------

  it('target=event calls eventsApi.vote instead of articlesApi', async () => {
    const wrapper = makeWrapper({ target: 'event', targetId: 'evt-1', initialVote: 0 })
    await wrapper.findAll('button')[0].trigger('click')
    expect(eventsApi.vote).toHaveBeenCalledWith('evt-1', 1)
    expect(articlesApi.vote).not.toHaveBeenCalled()
  })

  it('target=event calls eventsApi.removeVote on toggle off', async () => {
    const wrapper = makeWrapper({ target: 'event', targetId: 'evt-1', initialVote: 1 })
    await wrapper.findAll('button')[0].trigger('click')
    expect(eventsApi.removeVote).toHaveBeenCalledWith('evt-1')
    expect(articlesApi.removeVote).not.toHaveBeenCalled()
  })

  it('target=event emits vote-changed with the event id', async () => {
    const wrapper = makeWrapper({ target: 'event', targetId: 'evt-1', initialVote: 0 })
    await wrapper.findAll('button')[0].trigger('click')
    await new Promise(r => setTimeout(r, 10))
    expect(wrapper.emitted('vote-changed')![0]).toEqual([1, 'evt-1'])
  })
})
