// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { eventsApi, type Event } from '@/api/events'
import { digestApi, type Digest } from '@/api/digest'

interface FrontPageColumn {
  category_slug: string
  category_name: string
  events: Event[]
}

interface FrontPageData {
  hero: Event | null
  second_row: Event[]
  columns: FrontPageColumn[]
}

export const useFrontPageStore = defineStore('frontpage', () => {
  const data = ref<FrontPageData | null>(null)
  const digest = ref<Digest | null>(null)
  const digestDismissed = ref(false)
  const isLoading = ref(false)
  const isGeneratingDigest = ref(false)
  const lastUpdated = ref<Date | null>(null)
  const error = ref<string | null>(null)

  let refreshInterval: ReturnType<typeof setInterval> | null = null

  async function load(lang?: string) {
    isLoading.value = true
    error.value = null
    try {
      const res = await eventsApi.frontpage(lang)
      data.value = res.data
      lastUpdated.value = new Date()
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Errore nel caricamento'
    } finally {
      isLoading.value = false
    }
  }

  async function generateDigest() {
    isGeneratingDigest.value = true
    try {
      const res = await digestApi.generate({ max_articles: 30, force_fulltext: true })
      digest.value = res.data
      digestDismissed.value = false
    } finally {
      isGeneratingDigest.value = false
    }
  }

  function dismissDigest() {
    digestDismissed.value = true
  }

  function startAutoRefresh() {
    stopAutoRefresh()
    refreshInterval = setInterval(() => load(), 10 * 60 * 1000)
  }

  function stopAutoRefresh() {
    if (refreshInterval !== null) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
  }

  const showDigest = computed(() => digest.value !== null && !digestDismissed.value)

  return {
    data,
    digest,
    digestDismissed,
    isLoading,
    isGeneratingDigest,
    lastUpdated,
    error,
    showDigest,
    load,
    generateDigest,
    dismissDigest,
    startAutoRefresh,
    stopAutoRefresh,
  }
})
