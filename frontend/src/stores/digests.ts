// Copyright (C) 2026 Lorenzo Benfeati
// SPDX-License-Identifier: AGPL-3.0-or-later
import { ref } from 'vue'
import { defineStore } from 'pinia'
import { digestApi, type Digest } from '@/api/digest'

export const useDigestsStore = defineStore('digests', () => {
  const digests = ref<Digest[]>([])
  const pagination = ref({ total: 0, page: 1, pages: 1 })
  const isLoading = ref(false)

  async function load(append = false) {
    isLoading.value = true
    try {
      const page = append ? pagination.value.page + 1 : 1
      const res = await digestApi.list({ page, size: 20 })
      if (append) {
        digests.value = [...digests.value, ...res.data.items]
      } else {
        digests.value = res.data.items
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

  return { digests, pagination, isLoading, load, loadNextPage }
})
