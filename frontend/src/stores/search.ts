// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import { ref } from 'vue'
import { defineStore } from 'pinia'
import { searchApi, type SearchResult } from '@/api/search'

export const useSearchStore = defineStore('search', () => {
  const query = ref('')
  const results = ref<SearchResult[]>([])
  const total = ref(0)
  const page = ref(1)
  const isLoading = ref(false)
  const isOpen = ref(false)
  const error = ref<string | null>(null)

  let debounceTimer: ReturnType<typeof setTimeout> | null = null

  function open() {
    isOpen.value = true
  }

  function close() {
    isOpen.value = false
    query.value = ''
    results.value = []
    total.value = 0
    page.value = 1
    error.value = null
  }

  async function search(q: string, p: number = 1) {
    if (q.length < 2) {
      results.value = []
      total.value = 0
      return
    }
    isLoading.value = true
    error.value = null
    try {
      const res = await searchApi.search({ q, page: p, size: 20 })
      results.value = res.data.items
      total.value = res.data.total
      page.value = res.data.page
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      error.value = err.response?.data?.detail ?? 'Errore ricerca'
    } finally {
      isLoading.value = false
    }
  }

  function debouncedSearch(q: string) {
    query.value = q
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => search(q), 300)
  }

  return {
    query,
    results,
    total,
    page,
    isLoading,
    isOpen,
    error,
    open,
    close,
    search,
    debouncedSearch,
  }
})
