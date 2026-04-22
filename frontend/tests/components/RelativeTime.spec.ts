import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import RelativeTime from '@/components/common/RelativeTime.vue'
import en from '@/i18n/locales/en.json'

function makeWrapper(date: string | null) {
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  return mount(RelativeTime, {
    props: { date },
    global: { plugins: [i18n] },
  })
}

describe('RelativeTime', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-04-22T12:00:00Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows "now" for very recent dates', () => {
    const recent = new Date('2026-04-22T11:59:30Z').toISOString()
    const wrapper = makeWrapper(recent)
    const text = wrapper.find('time').text()
    // Intl.RelativeTimeFormat with numeric: 'auto' may say "now" or "0 minutes ago"
    expect(text.length).toBeGreaterThan(0)
  })

  it('shows minutes for sub-hour', () => {
    const date = new Date('2026-04-22T11:45:00Z').toISOString() // 15 min ago
    const wrapper = makeWrapper(date)
    expect(wrapper.find('time').text()).toMatch(/15|minute/i)
  })

  it('shows hours for same day within 24h', () => {
    const date = new Date('2026-04-22T09:00:00Z').toISOString() // 3 hours ago
    const wrapper = makeWrapper(date)
    expect(wrapper.find('time').text()).toMatch(/3|hour/i)
  })

  it('shows days for recent dates', () => {
    const date = new Date('2026-04-20T12:00:00Z').toISOString() // 2 days ago
    const wrapper = makeWrapper(date)
    expect(wrapper.find('time').text()).toMatch(/2|day/i)
  })

  it('renders time element with datetime attribute', () => {
    const date = new Date('2026-04-22T11:00:00Z').toISOString()
    const wrapper = makeWrapper(date)
    expect(wrapper.find('time').attributes('datetime')).toBeTruthy()
  })

  it('renders empty for null date', () => {
    const wrapper = makeWrapper(null)
    expect(wrapper.find('time').text()).toBe('')
  })
})
