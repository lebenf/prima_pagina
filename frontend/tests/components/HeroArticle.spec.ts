// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import HeroArticle from '@/components/frontpage/HeroArticle.vue'
import en from '@/i18n/locales/en.json'

const mockArticle = {
  id: 'a1',
  feed_id: 'f1',
  feed_title: 'Test Feed',
  title: 'Hero Article Title',
  url: 'https://example.com/article',
  author: 'John Doe',
  content_excerpt: '<p>This is the excerpt of the article.</p>',
  content_fulltext: null,
  fulltext_status: 'pending' as const,
  fulltext_loading: false,
  fulltext_fetched_at: null,
  language: 'en',
  tags: ['politics', 'world'],
  published_at: new Date('2026-04-22T10:00:00Z').toISOString(),
  fetched_at: new Date().toISOString(),
  is_read: false,
  is_starred: false,
  is_archived: false,
}

function makeWrapper(article = mockArticle) {
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  return mount(HeroArticle, {
    props: { article },
    global: { plugins: [i18n] },
  })
}

describe('HeroArticle', () => {
  it('renders article title', () => {
    const wrapper = makeWrapper()
    expect(wrapper.find('h2').text()).toContain('Hero Article Title')
  })

  it('renders excerpt text without HTML tags', () => {
    const wrapper = makeWrapper()
    const excerpt = wrapper.find('.hero-excerpt')
    expect(excerpt.text()).toContain('This is the excerpt of the article.')
    expect(excerpt.text()).not.toContain('<p>')
  })

  it('renders feed title', () => {
    const wrapper = makeWrapper()
    expect(wrapper.text()).toContain('Test Feed')
  })

  it('renders first tag as category label', () => {
    const wrapper = makeWrapper()
    expect(wrapper.find('.category-label').text()).toBe('politics')
  })

  it('emits click on article click', async () => {
    const wrapper = makeWrapper()
    await wrapper.find('article').trigger('click')
    expect(wrapper.emitted('click')).toBeTruthy()
  })

  it('star button does not propagate click to article', async () => {
    const wrapper = makeWrapper()
    const starBtn = wrapper.find('.action-btn')
    await starBtn.trigger('click')
    // toggle-star emitted, click should NOT be emitted via star button
    expect(wrapper.emitted('toggle-star')).toBeTruthy()
  })

  it('shows starred state', () => {
    const wrapper = makeWrapper({ ...mockArticle, is_starred: true })
    expect(wrapper.find('.action-btn').text()).toBe('★')
  })

  it('shows unstarred state', () => {
    const wrapper = makeWrapper({ ...mockArticle, is_starred: false })
    expect(wrapper.find('.action-btn').text()).toBe('☆')
  })
})
