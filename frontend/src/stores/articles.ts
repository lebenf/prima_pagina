import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { articlesApi, type Article, type ArticleFilters } from '@/api/articles'
import { useFeedsStore } from '@/stores/feeds'

export const useArticlesStore = defineStore('articles', () => {
  const articles = ref<Article[]>([])
  const selectedArticleId = ref<string | null>(null)
  const currentFeedId = ref<string | null>(null)
  const filters = ref<ArticleFilters>({
    is_read: undefined,
    is_starred: undefined,
    page: 1,
    size: 30,
    order_by: 'published_at',
    order_dir: 'desc',
  })
  const pagination = ref({ total: 0, page: 1, pages: 1, unread_count: 0 })
  const isLoading = ref(false)

  const selectedArticle = computed(() =>
    articles.value.find(a => a.id === selectedArticleId.value) ?? null
  )

  async function load(feedId?: string | null, append = false) {
    isLoading.value = true
    try {
      const params: ArticleFilters = { ...filters.value }
      if (feedId !== undefined) params.feed_id = feedId ?? undefined
      else if (currentFeedId.value) params.feed_id = currentFeedId.value

      const res = await articlesApi.list(params)
      if (append) {
        articles.value = [...articles.value, ...res.data.items]
      } else {
        articles.value = res.data.items
      }
      pagination.value = {
        total: res.data.total,
        page: res.data.page,
        pages: res.data.pages,
        unread_count: res.data.unread_count,
      }
    } finally {
      isLoading.value = false
    }
  }

  async function loadForFeed(feedId: string | null) {
    currentFeedId.value = feedId
    filters.value = { ...filters.value, page: 1 }
    selectedArticleId.value = null
    await load(feedId)
  }

  async function loadNextPage() {
    if (pagination.value.page >= pagination.value.pages) return
    filters.value = { ...filters.value, page: pagination.value.page + 1 }
    await load(currentFeedId.value, true)
  }

  async function markRead(articleId: string) {
    const article = articles.value.find(a => a.id === articleId)
    if (!article || article.is_read) return
    article.is_read = true
    try {
      await articlesApi.updateState(articleId, { is_read: true })
      const feedsStore = useFeedsStore()
      feedsStore.decrementUnread(article.feed_id)
    } catch {
      article.is_read = false
    }
  }

  async function toggleRead(articleId: string) {
    const article = articles.value.find(a => a.id === articleId)
    if (!article) return
    const newState = !article.is_read
    article.is_read = newState
    try {
      await articlesApi.updateState(articleId, { is_read: newState })
      const feedsStore = useFeedsStore()
      if (newState) feedsStore.decrementUnread(article.feed_id)
    } catch {
      article.is_read = !newState
    }
  }

  async function toggleStar(articleId: string) {
    const article = articles.value.find(a => a.id === articleId)
    if (!article) return
    const newState = !article.is_starred
    article.is_starred = newState
    try {
      await articlesApi.updateState(articleId, { is_starred: newState })
    } catch {
      article.is_starred = !newState
    }
  }

  function setFilter(key: keyof ArticleFilters, value: unknown) {
    filters.value = { ...filters.value, [key]: value, page: 1 }
  }

  function updateArticle(updated: Partial<Article> & { id: string }) {
    const idx = articles.value.findIndex(a => a.id === updated.id)
    if (idx !== -1) articles.value[idx] = { ...articles.value[idx], ...updated }
  }

  return {
    articles,
    selectedArticleId,
    selectedArticle,
    currentFeedId,
    filters,
    pagination,
    isLoading,
    load,
    loadForFeed,
    loadNextPage,
    markRead,
    toggleRead,
    toggleStar,
    setFilter,
    updateArticle,
  }
})
