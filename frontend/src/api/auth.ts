// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import client from './client'

export interface User {
  id: string
  email: string
  username: string
  preferred_lang: string
  role: 'admin' | 'user'
  is_active: boolean
}

export interface Session {
  id: string
  created_at: string
  expires_at: string
  last_active_at: string
  ip_address: string | null
  user_agent: string | null
  is_current: boolean
}

export const authApi = {
  login: (username: string, password: string) =>
    client.post<User>('/auth/login', { username, password }),

  logout: () =>
    client.post('/auth/logout'),

  me: () =>
    client.get<User>('/auth/me'),

  sessions: () =>
    client.get<Session[]>('/auth/sessions'),

  revokeSession: (id: string) =>
    client.delete(`/auth/sessions/${id}`),

  updateMe: (data: Partial<Pick<User, 'preferred_lang'>>) =>
    client.patch<User>('/auth/me', data),
}
