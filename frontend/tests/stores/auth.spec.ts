// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

// Mock the API and i18n modules
vi.mock('@/api/auth', () => ({
  authApi: {
    me: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
  },
}))

vi.mock('@/i18n', () => ({
  setLocale: vi.fn(),
}))

import { authApi } from '@/api/auth'

const mockUser = {
  id: 'user-1',
  email: 'test@example.com',
  username: 'testuser',
  preferred_lang: 'it',
  role: 'user' as const,
  is_active: true,
}

const mockAdmin = { ...mockUser, role: 'admin' as const }

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('login sets user', async () => {
    vi.mocked(authApi.login).mockResolvedValueOnce({ data: mockUser } as any)

    const store = useAuthStore()
    expect(store.user).toBeNull()

    await store.login('testuser', 'password')

    expect(store.user).toEqual(mockUser)
    expect(store.isAuthenticated).toBe(true)
  })

  it('logout clears user', async () => {
    vi.mocked(authApi.logout).mockResolvedValueOnce({} as any)

    const store = useAuthStore()
    store.user = mockUser

    await store.logout()

    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
  })

  it('fetchMe handles 401 gracefully', async () => {
    vi.mocked(authApi.me).mockRejectedValueOnce({ response: { status: 401 } })

    const store = useAuthStore()
    await store.fetchMe()

    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
  })

  it('isAdmin computed reflects role', () => {
    const store = useAuthStore()

    store.user = mockUser
    expect(store.isAdmin).toBe(false)

    store.user = mockAdmin
    expect(store.isAdmin).toBe(true)
  })
})
