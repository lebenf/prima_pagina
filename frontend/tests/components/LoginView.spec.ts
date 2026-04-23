// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createI18n } from 'vue-i18n'
import LoginView from '@/views/LoginView.vue'
import { useAuthStore } from '@/stores/auth'
import en from '@/i18n/locales/en.json'

vi.mock('@/i18n', () => ({
  setLocale: vi.fn(),
}))

function makeWrapper() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', component: LoginView },
      { path: '/', component: { template: '<div>Home</div>' } },
    ],
  })

  const i18n = createI18n({
    legacy: false,
    locale: 'en',
    messages: { en },
  })

  return mount(LoginView, {
    global: {
      plugins: [createPinia(), router, i18n],
    },
  })
}

describe('LoginView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('renders login form', () => {
    const wrapper = makeWrapper()
    expect(wrapper.find('input[type="text"]').exists()).toBe(true)
    expect(wrapper.find('input[type="password"]').exists()).toBe(true)
    expect(wrapper.find('button[type="submit"]').exists()).toBe(true)
  })

  it('shows error on failed login', async () => {
    const wrapper = makeWrapper()
    const store = useAuthStore()
    vi.spyOn(store, 'login').mockRejectedValueOnce(new Error('Invalid credentials'))

    await wrapper.find('input[type="text"]').setValue('bad')
    await wrapper.find('input[type="password"]').setValue('wrong')
    await wrapper.find('form').trigger('submit')

    // Wait for the async operation
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
  })

  it('submit button disabled while loading', async () => {
    const wrapper = makeWrapper()
    const store = useAuthStore()
    store.isLoading = true
    await wrapper.vm.$nextTick()

    const btn = wrapper.find('button[type="submit"]')
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('submit button disabled when fields are empty', () => {
    const wrapper = makeWrapper()
    const btn = wrapper.find('button[type="submit"]')
    expect(btn.attributes('disabled')).toBeDefined()
  })
})
