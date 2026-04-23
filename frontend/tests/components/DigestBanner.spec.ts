// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import DigestBanner from '@/components/frontpage/DigestBanner.vue'
import en from '@/i18n/locales/en.json'

const mockDigest = {
  id: 'd1',
  title: 'Press Digest — 21 April 2026',
  period_start: '2026-04-21T00:00:00',
  period_end: '2026-04-22T00:00:00',
  content_html: '<h2>News</h2>',
  content_text: 'News',
  virtual_feed_id: null,
  llm_provider: 'claude',
  llm_model: 'claude-opus-4-7',
  article_count: 12,
  created_at: '2026-04-22T07:00:00',
}

function makeWrapper(digest = mockDigest) {
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  return mount(DigestBanner, {
    props: { digest },
    global: { plugins: [i18n] },
  })
}

describe('DigestBanner', () => {
  it('renders digest title', () => {
    const wrapper = makeWrapper()
    expect(wrapper.text()).toContain('Press Digest — 21 April 2026')
  })

  it('renders article count', () => {
    const wrapper = makeWrapper()
    expect(wrapper.text()).toContain('12')
  })

  it('renders provider info', () => {
    const wrapper = makeWrapper()
    expect(wrapper.text()).toContain('claude')
  })

  it('emits dismiss on close click', async () => {
    const wrapper = makeWrapper()
    const closeBtn = wrapper.findAll('button').find(b => b.text().includes('×'))
    await closeBtn!.trigger('click')
    expect(wrapper.emitted('dismiss')).toBeTruthy()
  })

  it('emits open on read click', async () => {
    const wrapper = makeWrapper()
    const readBtn = wrapper.findAll('button').find(b => b.text().includes('Read'))
    await readBtn!.trigger('click')
    expect(wrapper.emitted('open')).toBeTruthy()
  })
})
