import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { articlesApi, type Article } from '@/api/articles'
import { digestApi, type Digest } from '@/api/digest'

interface FrontPageColumn {
  category_slug: string
  category_name: string
  articles: Article[]
}

interface FrontPageData {
  hero: Article | null
  second_row: Article[]
  columns: FrontPageColumn[]
  digest_available: boolean
  digest_id: string | null
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
      const res = await articlesApi.frontpage(lang)
      data.value = res.data
      lastUpdated.value = new Date()

      if (res.data.digest_available && res.data.digest_id) {
        await loadDigest(res.data.digest_id)
      }
    } catch (e: any) {
      error.value = e.response?.data?.detail || 'Errore nel caricamento'
    } finally {
      isLoading.value = false
    }
  }

  async function loadDigest(id: string) {
    try {
      const res = await digestApi.get(id)
      digest.value = res.data
    } catch {
      // digest non critico: ignora errori
    }
  }

  async function generateDigest() {
    isGeneratingDigest.value = true
    try {
      const res = await digestApi.generate({ max_articles: 30, force_fulltext: true })
      digest.value = res.data
      digestDismissed.value = false
      if (data.value) {
        data.value.digest_available = true
        data.value.digest_id = res.data.id
      }
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
    loadDigest,
    generateDigest,
    dismissDigest,
    startAutoRefresh,
    stopAutoRefresh,
  }
})
