// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import LlmFunctionAssignments from '@/components/admin/LlmFunctionAssignments.vue'
import en from '@/i18n/locales/en.json'

const { mockListFn, mockUpdateFn } = vi.hoisted(() => ({
  mockListFn: vi.fn(),
  mockUpdateFn: vi.fn(),
}))

vi.mock('@/api/admin', () => ({
  adminApi: {
    llmFunctions: {
      list: mockListFn,
      update: mockUpdateFn,
    },
  },
}))

const mockRows = [
  { function: 'tagging', primary_config_id: null, fallback_config_id: null },
  { function: 'event_summary', primary_config_id: null, fallback_config_id: null },
  { function: 'extraction_script', primary_config_id: null, fallback_config_id: null },
  { function: 'related_articles', primary_config_id: null, fallback_config_id: null },
  { function: 'digest', primary_config_id: null, fallback_config_id: null },
]

const mockConfigs = [
  { id: 'cfg-1', provider: 'ollama', label: null, model_name: 'llama3.2', endpoint_url: null, has_api_key: false, is_active: true, timeout_sec: 300, max_concurrent: 1, tagging_language: 'it', created_at: '2026-01-01' },
  { id: 'cfg-2', provider: 'mistral', label: 'Mistral prod', model_name: 'mistral-large-latest', endpoint_url: null, has_api_key: true, is_active: true, timeout_sec: 300, max_concurrent: 1, tagging_language: 'it', created_at: '2026-01-01' },
]

function makeWrapper() {
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  return mount(LlmFunctionAssignments, {
    props: { configs: mockConfigs as any },
    global: { plugins: [i18n] },
  })
}

describe('LlmFunctionAssignments', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListFn.mockResolvedValue({ data: mockRows })
    mockUpdateFn.mockResolvedValue({ data: mockRows[0] })
  })

  it('renders all five function rows', async () => {
    const wrapper = makeWrapper()
    await flushPromises()
    const rows = wrapper.findAll('tbody tr')
    expect(rows).toHaveLength(5)
  })

  it('shows mistral as a provider option', async () => {
    const wrapper = makeWrapper()
    await flushPromises()
    expect(wrapper.text()).toContain('mistral — mistral-large-latest')
  })

  it('saves assignment on save button click', async () => {
    const wrapper = makeWrapper()
    await flushPromises()

    const firstRow = wrapper.findAll('tbody tr')[0]
    const select = firstRow.find('select')
    await select.setValue('cfg-2')

    const saveBtn = firstRow.find('button')
    await saveBtn.trigger('click')
    await flushPromises()

    expect(mockUpdateFn).toHaveBeenCalledWith('tagging', {
      primary_config_id: 'cfg-2',
      fallback_config_id: null,
    })
  })

  it('shows saved confirmation after successful save', async () => {
    const wrapper = makeWrapper()
    await flushPromises()

    const firstRow = wrapper.findAll('tbody tr')[0]
    await firstRow.find('button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Assignment updated')
  })
})
