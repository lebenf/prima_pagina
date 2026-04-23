// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { authApi, type User } from '@/api/auth'
import { setLocale } from '@/i18n'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const isLoading = ref(false)

  const isAuthenticated = computed(() => user.value !== null)
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function fetchMe() {
    try {
      const res = await authApi.me()
      user.value = res.data
      await setLocale(res.data.preferred_lang)
    } catch {
      user.value = null
    }
  }

  async function login(username: string, password: string) {
    isLoading.value = true
    try {
      const res = await authApi.login(username, password)
      user.value = res.data
      await setLocale(res.data.preferred_lang)
    } finally {
      isLoading.value = false
    }
  }

  async function logout() {
    try {
      await authApi.logout()
    } finally {
      user.value = null
    }
  }

  function clearUser() {
    user.value = null
  }

  return { user, isLoading, isAuthenticated, isAdmin, fetchMe, login, logout, clearUser }
})
