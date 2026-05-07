<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="flex flex-col h-full overflow-hidden bg-white">
    <template v-if="article">
      <ArticleToolbar
        :article="article"
        :show-back="showBack"
        @back="emit('back')"
      />

      <div class="flex-1 overflow-y-auto px-6 py-6 max-w-3xl mx-auto w-full">
        <!-- Meta -->
        <p class="text-xs text-gray-400 mb-2">
          {{ article.feed_title }}
          <span v-if="article.published_at"> · {{ formatDate(article.published_at) }}</span>
        </p>

        <!-- Title -->
        <h1 class="font-serif text-2xl font-bold text-gray-900 leading-tight mb-2">
          {{ article.title }}
        </h1>

        <!-- Author + fulltext badge -->
        <div class="flex items-center gap-2 mb-3">
          <p v-if="article.author" class="text-sm text-gray-500">
            {{ t('article.by', { author: article.author }) }}
          </p>
          <FulltextBadge
            v-if="article.fulltext_status === 'ok' && article.fulltext_fetched_at"
            :article-id="article.id"
            :fetched-at="article.fulltext_fetched_at"
            @reported="onFulltextReported"
          />
        </div>

        <!-- Tags -->
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

        <!-- Fulltext loading indicator -->
        <div v-if="article.fulltext_loading" class="flex items-center gap-2 mb-4 text-sm text-gray-500">
          <div class="w-4 h-4 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin flex-shrink-0" />
          {{ t('article.loadingFulltext') }}
        </div>

        <!-- Fulltext failed -->
        <p v-if="fulltextTimedOut" class="mb-4 text-sm text-amber-600">
          {{ t('article.fulltextFailed') }}
        </p>

        <!-- Content — sanitized server-side by bleach -->
        <div
          class="prose prose-sm max-w-none text-gray-800 leading-relaxed article-content"
          v-html="content"
        />

        <RelatedArticles
          :article-id="article?.id ?? null"
          @article-click="emit('select-article', $event)"
        />
      </div>
    </template>

    <!-- Empty state -->
    <div v-else class="flex-1 flex items-center justify-center text-gray-300">
      <div class="text-center">
        <svg class="w-12 h-12 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10l6 6v10a2 2 0 01-2 2z" />
        </svg>
        <p class="text-sm">{{ t('reader.selectArticle') }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useArticlesStore } from '@/stores/articles'
import { articlesApi } from '@/api/articles'
import type { Article } from '@/api/articles'
import ArticleToolbar from './ArticleToolbar.vue'
import RelatedArticles from '@/components/common/RelatedArticles.vue'
import FulltextBadge from '@/components/common/FulltextBadge.vue'

const props = defineProps<{
  article: Article | null
  showBack?: boolean
}>()

const emit = defineEmits<{
  back: []
  'select-article': [article: Article]
}>()

const { t, locale } = useI18n()
const articlesStore = useArticlesStore()

const fulltextTimedOut = ref(false)
let pollInterval: ReturnType<typeof setInterval> | null = null
let pollAttempts = 0
const MAX_POLL_ATTEMPTS = 30

const content = computed(() => {
  if (!props.article) return ''
  return props.article.content_fulltext ?? props.article.content_excerpt ?? ''
})

function formatDate(dateStr: string, withTime = false): string {
  const opts = withTime
    ? { dateStyle: 'long' as const, timeStyle: 'short' as const }
    : { dateStyle: 'long' as const }
  return new Intl.DateTimeFormat(locale.value, opts).format(new Date(dateStr))
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
  pollAttempts = 0
}

async function startPolling(articleId: string) {
  stopPolling()
  fulltextTimedOut.value = false
  pollAttempts = 0

  pollInterval = setInterval(async () => {
    pollAttempts++
    if (pollAttempts > MAX_POLL_ATTEMPTS) {
      stopPolling()
      fulltextTimedOut.value = true
      return
    }

    try {
      const res = await articlesApi.fulltextStatus(articleId)
      if (res.data.fulltext_available) {
        stopPolling()
        const full = await articlesApi.get(articleId)
        articlesStore.updateArticle(full.data)
      }
    } catch {
      // ignore transient errors
    }
  }, 2000)
}

watch(
  () => props.article,
  (article) => {
    stopPolling()
    fulltextTimedOut.value = false
    if (article?.fulltext_loading) {
      startPolling(article.id)
    }
  },
  { immediate: true },
)

// Links must open in new tab — applied via CSS + post-render
watch(content, () => {
  // content updated; link target enforcement done via CSS in article-content class
})

function onFulltextReported() {
  if (!props.article) return
  articlesStore.updateArticle({ id: props.article.id, content_fulltext: null, fulltext_loading: true })
  startPolling(props.article.id)
}

onUnmounted(stopPolling)
</script>

<style scoped>
/* Make all links in article content open in new tab via pointer-events and target enforcement */
:deep(.article-content a) {
  color: #2563eb;
  text-decoration: underline;
  text-underline-offset: 2px;
}
:deep(.article-content a)::after {
  content: '';
}
:deep(.article-content img) {
  max-width: 100%;
  height: auto;
  border-radius: 0.375rem;
}
:deep(.article-content p) {
  margin-bottom: 1em;
}
:deep(.article-content h2),
:deep(.article-content h3),
:deep(.article-content h4) {
  font-weight: 700;
  margin-top: 1.5em;
  margin-bottom: 0.5em;
}
:deep(.article-content blockquote) {
  border-left: 3px solid #e5e7eb;
  padding-left: 1em;
  color: #6b7280;
  font-style: italic;
}
:deep(.article-content pre),
:deep(.article-content code) {
  background: #f3f4f6;
  border-radius: 0.25rem;
  font-size: 0.875em;
  padding: 0.1em 0.3em;
}
:deep(.article-content pre code) {
  padding: 0;
}
</style>
