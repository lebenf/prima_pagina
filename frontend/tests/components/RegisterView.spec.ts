// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createI18n } from 'vue-i18n'
import RegisterView from '@/views/RegisterView.vue'
import en from '@/i18n/locales/en.json'

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    isAuthenticated: false,
    fetchMe: vi.fn().mockResolvedValue(undefined),
  }),
}))

import client from '@/api/client'

function makeRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/join', component: RegisterView },
      { path: '/login', component: { template: '<div>Login</div>' } },
      { path: '/', component: { template: '<div>Home</div>' } },
    ],
  })
}

async function makeWrapper(token = 'valid-token') {
  const router = makeRouter()
  await router.push(`/join?token=${token}`)
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  return mount(RegisterView, {
    global: {
      plugins: [createPinia(), router, i18n],
      stubs: { RouterLink: { template: '<a><slot /></a>' } },
    },
  })
}

describe('RegisterView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('shows error state when token is invalid', async () => {
    vi.mocked(client.get).mockRejectedValueOnce({ response: { status: 404 } })
    const wrapper = await makeWrapper('bad-token')
    await flushPromises()
    expect(wrapper.text()).toContain('Invalid invite')
  })

  it('prefills email from invite response', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({ data: { valid: true, email: 'user@example.com', invited_by: 'admin' } })
    const wrapper = await makeWrapper()
    await flushPromises()
    const emailInput = wrapper.find('input[type="email"]')
    expect((emailInput.element as HTMLInputElement).value).toBe('user@example.com')
  })

  it('shows password mismatch error', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({ data: { valid: true, email: null, invited_by: 'admin' } })
    const wrapper = await makeWrapper()
    await flushPromises()
    const inputs = wrapper.findAll('input[type="password"]')
    await inputs[0].setValue('password123')
    await inputs[1].setValue('different456')
    expect(wrapper.text()).toContain('Passwords do not match')
  })

  it('calls register endpoint and redirects on success', async () => {
    vi.mocked(client.get).mockResolvedValueOnce({ data: { valid: true, email: null, invited_by: 'admin' } })
    vi.mocked(client.post).mockResolvedValueOnce({ data: {} })
    const wrapper = await makeWrapper()
    await flushPromises()

    await wrapper.find('input[type="text"]').setValue('newuser')
    await wrapper.find('input[type="email"]').setValue('new@example.com')
    const pwInputs = wrapper.findAll('input[type="password"]')
    await pwInputs[0].setValue('securepass1')
    await pwInputs[1].setValue('securepass1')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(client.post).toHaveBeenCalledWith(
      expect.stringContaining('/auth/register/'),
      expect.objectContaining({ username: 'newuser' }),
    )
  })
})
