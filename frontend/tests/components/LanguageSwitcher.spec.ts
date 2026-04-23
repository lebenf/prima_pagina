// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createI18n } from 'vue-i18n'
import LanguageSwitcher from '@/components/common/LanguageSwitcher.vue'
import en from '@/i18n/locales/en.json'

// Use vi.hoisted so the mock reference is available when vi.mock factory runs
const { mockSetLocale } = vi.hoisted(() => ({
  mockSetLocale: vi.fn(),
}))

vi.mock('@/i18n', () => ({
  setLocale: mockSetLocale,
  SUPPORTED_LOCALES: ['it', 'en', 'fr', 'de', 'es', 'pt'],
}))

vi.mock('@/api/auth', () => ({
  authApi: {
    updateMe: vi.fn(),
  },
}))

function makeWrapper() {
  const i18n = createI18n({
    legacy: false,
    locale: 'en',
    messages: { en },
  })

  return mount(LanguageSwitcher, {
    global: {
      plugins: [createPinia(), i18n],
    },
  })
}

describe('LanguageSwitcher', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('renders the toggle button', () => {
    const wrapper = makeWrapper()
    expect(wrapper.find('button').exists()).toBe(true)
  })

  it('opens dropdown on click showing language options', async () => {
    const wrapper = makeWrapper()
    await wrapper.find('button').trigger('click')
    await wrapper.vm.$nextTick()

    // The dropdown buttons (language options) should now be visible
    const allButtons = wrapper.findAll('button')
    // Toggle button + 6 language options
    expect(allButtons.length).toBe(7)
  })

  it('calls setLocale when a language is selected', async () => {
    const wrapper = makeWrapper()
    await wrapper.find('button').trigger('click')
    await wrapper.vm.$nextTick()

    const buttons = wrapper.findAll('button')
    // buttons[1] is the first language option (it)
    await buttons[1].trigger('click')
    expect(mockSetLocale).toHaveBeenCalled()
  })
})
