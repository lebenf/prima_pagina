// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import { ref } from 'vue'
import { defineStore } from 'pinia'
import { eventsApi, type Event } from '@/api/events'

export const useEventsStore = defineStore('events', () => {
  const events = ref<Event[]>([])
  const pagination = ref({ total: 0, page: 1, pages: 1 })
  const isLoading = ref(false)

  async function load(append = false) {
    isLoading.value = true
    try {
      const page = append ? pagination.value.page + 1 : 1
      const res = await eventsApi.list({ page, size: 20 })
      if (append) {
        events.value = [...events.value, ...res.data.items]
      } else {
        events.value = res.data.items
      }
      pagination.value = {
        total: res.data.total,
        page: res.data.page,
        pages: res.data.pages,
      }
    } finally {
      isLoading.value = false
    }
  }

  async function loadNextPage() {
    if (pagination.value.page >= pagination.value.pages) return
    await load(true)
  }

  return { events, pagination, isLoading, load, loadNextPage }
})
