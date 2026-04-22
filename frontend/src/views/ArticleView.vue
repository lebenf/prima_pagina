<template>
  <div class="flex flex-col h-full overflow-hidden bg-white">
    <template v-if="article">
      <ArticleToolbar
        :article="article"
        :show-back="true"
        @back="router.back()"
      />

      <div class="flex-1 overflow-y-auto px-6 py-6 max-w-3xl mx-auto w-full">
        <p class="text-xs text-gray-400 mb-2">
          {{ article.feed_title }}
          <span v-if="article.published_at"> · {{ formatDate(article.published_at) }}</span>
        </p>

        <h1 class="font-serif text-2xl font-bold text-gray-900 leading-tight mb-2">
          {{ article.title }}
        </h1>

        <p v-if="article.author" class="text-sm text-gray-500 mb-3">
          {{ t('article.by', { author: article.author }) }}
        </p>

        <div v-if="article.tags.length > 0" class="flex flex-wrap gap-1.5 mb-4">
          <span
            v-for="tag in article.tags"
            :key="tag"
            class="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded-full"
          >
            {{ tag }}
          </span>
        </div>

        <hr class="border-gray-200 mb-5" />

        <div v-if="article.fulltext_loading" class="flex items-center gap-2 mb-4 text-sm text-gray-500">
          <div class="w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin flex-shrink-0" />
          {{ t('article.loadingFulltext') }}
        </div>

        <p v-if="fulltextTimedOut" class="mb-4 text-sm text-amber-600">
          {{ t('article.fulltextFailed') }}
        </p>

        <!-- Content — sanitized server-side by bleach -->
        <div
          class="prose prose-sm max-w-none text-gray-800 leading-relaxed article-content"
          v-html="content"
        />
      </div>
    </template>

    <div v-else-if="isLoading" class="flex-1 flex items-center justify-center">
      <div class="w-8 h-8 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
    </div>

    <div v-else class="flex-1 flex items-center justify-center text-gray-400">
      <p>{{ t('common.error') }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { articlesApi, type Article } from '@/api/articles'
import { useArticlesStore } from '@/stores/articles'
import ArticleToolbar from '@/components/reader/ArticleToolbar.vue'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const articlesStore = useArticlesStore()

const article = ref<Article | null>(null)
const isLoading = ref(false)
const fulltextTimedOut = ref(false)

let pollInterval: ReturnType<typeof setInterval> | null = null
let pollAttempts = 0
const MAX_POLL_ATTEMPTS = 30

const content = computed(() =>
  article.value?.content_fulltext ?? article.value?.content_excerpt ?? ''
)

function formatDate(dateStr: string): string {
  return new Intl.DateTimeFormat(locale.value, { dateStyle: 'long' }).format(new Date(dateStr))
}

function stopPolling() {
  if (pollInterval) { clearInterval(pollInterval); pollInterval = null }
  pollAttempts = 0
}

async function startPolling(id: string) {
  stopPolling()
  pollInterval = setInterval(async () => {
    pollAttempts++
    if (pollAttempts > MAX_POLL_ATTEMPTS) { stopPolling(); fulltextTimedOut.value = true; return }
    try {
      const res = await articlesApi.fulltextStatus(id)
      if (res.data.fulltext_available) {
        stopPolling()
        const full = await articlesApi.get(id)
        article.value = full.data
        articlesStore.updateArticle(full.data)
      }
    } catch { /* ignore transient errors */ }
  }, 2000)
}

async function load(id: string) {
  isLoading.value = true
  stopPolling()
  fulltextTimedOut.value = false
  try {
    const res = await articlesApi.get(id)
    article.value = res.data
    articlesStore.updateArticle(res.data)
    if (!res.data.is_read) articlesStore.markRead(id)
    if (res.data.fulltext_loading) startPolling(id)
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  const id = route.params.id as string
  if (id) load(id)
})

watch(() => route.params.id, (id) => {
  if (id) load(id as string)
})

onUnmounted(stopPolling)
</script>

<style scoped>
:deep(.article-content a) { color: #2563eb; text-decoration: underline; text-underline-offset: 2px; }
:deep(.article-content img) { max-width: 100%; height: auto; border-radius: 0.375rem; }
:deep(.article-content p) { margin-bottom: 1em; }
:deep(.article-content h2), :deep(.article-content h3), :deep(.article-content h4) { font-weight: 700; margin-top: 1.5em; margin-bottom: 0.5em; }
:deep(.article-content blockquote) { border-left: 3px solid #e5e7eb; padding-left: 1em; color: #6b7280; font-style: italic; }
:deep(.article-content pre), :deep(.article-content code) { background: #f3f4f6; border-radius: 0.25rem; font-size: 0.875em; padding: 0.1em 0.3em; }
</style>
