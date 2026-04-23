// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { createPinia, setActivePinia } from 'pinia'
import AdminUsers from '@/components/admin/AdminUsers.vue'
import en from '@/i18n/locales/en.json'

const { mockListFn, mockDeleteFn } = vi.hoisted(() => ({
  mockListFn: vi.fn(),
  mockDeleteFn: vi.fn(),
}))

vi.mock('@/api/admin', () => ({
  adminApi: {
    users: {
      list: mockListFn,
      create: vi.fn(),
      update: vi.fn(),
      delete: mockDeleteFn,
    },
  },
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    user: { id: 'u1', role: 'admin' },
    isAdmin: true,
  }),
}))

const mockUsers = [
  { id: 'u1', username: 'admin', email: 'admin@example.com', role: 'admin', preferred_lang: 'it', is_active: true, created_at: '2026-01-01' },
  { id: 'u2', username: 'mario', email: 'mario@example.com', role: 'user', preferred_lang: 'it', is_active: true, created_at: '2026-01-02' },
]

function makeWrapper() {
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  setActivePinia(createPinia())
  return mount(AdminUsers, {
    global: {
      plugins: [i18n],
      stubs: {
        UserFormModal: true,
        ConfirmDialog: true,
        Teleport: true,
      },
    },
  })
}

describe('AdminUsers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListFn.mockResolvedValue({ data: mockUsers })
    mockDeleteFn.mockResolvedValue({})
  })

  it('renders user list after load', async () => {
    const wrapper = makeWrapper()
    await flushPromises()
    expect(wrapper.text()).toContain('admin')
    expect(wrapper.text()).toContain('mario')
  })

  it('opens create modal on new user button click', async () => {
    const wrapper = makeWrapper()
    await flushPromises()
    const btn = wrapper.findAll('button').find(b => b.text().includes('New user'))
    await btn!.trigger('click')
    expect(wrapper.findComponent({ name: 'UserFormModal' }).exists()).toBe(true)
  })

  it('cannot delete current user — delete button disabled', async () => {
    const wrapper = makeWrapper()
    await flushPromises()
    const rows = wrapper.findAll('tbody tr')
    const deleteBtn = rows[0].findAll('button').find(b => b.text().includes('🗑️'))
    expect(deleteBtn!.attributes('disabled')).toBeDefined()
  })

  it('shows confirm dialog on delete of other user', async () => {
    const wrapper = makeWrapper()
    await flushPromises()
    const rows = wrapper.findAll('tbody tr')
    const deleteBtn = rows[1].findAll('button').find(b => b.text().includes('🗑️'))
    await deleteBtn!.trigger('click')
    expect(wrapper.findComponent({ name: 'ConfirmDialog' }).exists()).toBe(true)
  })
})
