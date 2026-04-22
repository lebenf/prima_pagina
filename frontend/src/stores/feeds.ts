import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { feedsApi, type Feed } from '@/api/feeds'
import { articlesApi } from '@/api/articles'

export const useFeedsStore = defineStore('feeds', () => {
  const feeds = ref<Feed[]>([])
  const unreadCounts = ref<Record<string, number>>({})
  const selectedFeedId = ref<string | null>(null)
  const isLoading = ref(false)

  async function loadSubscribed() {
    isLoading.value = true
    try {
      const res = await feedsApi.subscribed()
      feeds.value = res.data
      await loadUnreadCounts()
    } finally {
      isLoading.value = false
    }
  }

  async function loadUnreadCounts() {
    if (feeds.value.length === 0) return
    try {
      const res = await articlesApi.list({ is_read: false, size: 500 })
      const counts: Record<string, number> = {}
      for (const article of res.data.items) {
        counts[article.feed_id] = (counts[article.feed_id] ?? 0) + 1
      }
      unreadCounts.value = counts
    } catch {
      // non-critical
    }
  }

  function decrementUnread(feedId: string, count = 1) {
    if (unreadCounts.value[feedId]) {
      unreadCounts.value[feedId] = Math.max(0, unreadCounts.value[feedId] - count)
    }
  }

  function setUnreadCount(feedId: string, count: number) {
    unreadCounts.value[feedId] = count
  }

  const feedsWithCounts = computed(() =>
    feeds.value.map(f => ({
      ...f,
      unread_count: unreadCounts.value[f.id] ?? 0,
    }))
  )

  const totalUnread = computed(() =>
    Object.values(unreadCounts.value).reduce((s, n) => s + n, 0)
  )

  return {
    feeds,
    unreadCounts,
    selectedFeedId,
    isLoading,
    feedsWithCounts,
    totalUnread,
    loadSubscribed,
    loadUnreadCounts,
    decrementUnread,
    setUnreadCount,
  }
})
