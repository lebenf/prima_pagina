// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { createPinia, setActivePinia } from 'pinia'
import AdminLLMConfigs from '@/components/admin/AdminLLMConfigs.vue'
import en from '@/i18n/locales/en.json'

const { mockListFn, mockHealthCheckFn, mockDeleteFn } = vi.hoisted(() => ({
  mockListFn: vi.fn(),
  mockHealthCheckFn: vi.fn(),
  mockDeleteFn: vi.fn(),
}))

vi.mock('@/api/admin', () => ({
  adminApi: {
    llm: {
      list: mockListFn,
      healthCheck: mockHealthCheckFn,
      delete: mockDeleteFn,
    },
  },
}))

const mockConfigs = [
  {
    id: 'llm1',
    provider: 'claude',
    label: 'Claude Sonnet',
    model_name: 'claude-sonnet-4-5',
    endpoint_url: null,
    has_api_key: true,
    use_for: ['digest'],
    is_default: true,
    is_active: true,
    priority: 10,
    created_at: '2026-01-01',
  },
]

function makeWrapper() {
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  setActivePinia(createPinia())
  return mount(AdminLLMConfigs, {
    global: {
      plugins: [i18n],
      stubs: { LLMConfigFormModal: true, ConfirmDialog: true, Teleport: true },
    },
  })
}

describe('AdminLLMConfigs', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListFn.mockResolvedValue({ data: mockConfigs })
    mockHealthCheckFn.mockResolvedValue({ data: { ok: true, latency_ms: 45, error: null } })
    mockDeleteFn.mockResolvedValue({})
  })

  it('shows has_api_key badge not key value', async () => {
    const wrapper = makeWrapper()
    await flushPromises()
    expect(wrapper.text()).toContain('Has API key')
    expect(wrapper.text()).not.toContain('sk-ant')
  })

  it('health check button calls API and shows result inline', async () => {
    const wrapper = makeWrapper()
    await flushPromises()
    const btn = wrapper.findAll('button').find(b => b.text().includes('Health check'))
    await btn!.trigger('click')
    await flushPromises()
    expect(mockHealthCheckFn).toHaveBeenCalledWith('llm1')
    expect(wrapper.text()).toContain('OK')
    expect(wrapper.text()).toContain('45ms')
  })
})
