<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <Teleport to="body">
    <Transition name="drawer-slide">
      <div
        v-if="isOpen"
        class="drawer-overlay"
        role="dialog"
        aria-modal="true"
        :aria-label="article?.title || t('article.reading')"
        @click.self="close"
      >
        <div class="drawer-panel">

          <header class="drawer-header">
            <button class="drawer-close" :aria-label="t('common.close')" @click="close">✕</button>
            <div class="drawer-actions">
              <VoteButtons
                v-if="article"
                :article-id="article.id"
                :initial-vote="article.user_vote ?? 0"
                :compact="false"
                @vote-changed="onVoteChanged"
              />
              <button
                v-if="article"
                class="action-btn"
                @click="toggleStar"
              >{{ article.is_starred ? '★' : '☆' }}</button>
              <a
                v-if="article?.url"
                :href="article.url"
                target="_blank"
                rel="noopener noreferrer"
                class="action-btn"
                :title="t('article.openOriginal')"
              >↗</a>
              <RouterLink
                v-if="article"
                :to="{ name: 'reader', query: { article: article.id } }"
                class="action-btn open-reader-btn"
                @click="close"
              >
                {{ t('article.openInReader') }}
              </RouterLink>
            </div>
          </header>

          <div v-if="isLoading" class="drawer-loading">
            <LoadingSpinner />
          </div>

          <article v-else-if="article" class="drawer-content">
            <div class="article-meta">
              <span class="feed-name">{{ article.feed_title }}</span>
              <span v-if="article.feed_title" class="separator">·</span>
              <RelativeTime v-if="article.published_at" :date="article.published_at" />
              <span v-if="article.author" class="separator">·</span>
              <span v-if="article.author" class="author">{{ article.author }}</span>
            </div>

            <h1 class="article-title">{{ article.title }}</h1>

            <div v-if="article.tags.length" class="article-tags">
              <span v-for="tag in article.tags" :key="tag" class="tag">{{ tag }}</span>
            </div>

            <div v-if="article.fulltext_loading" class="fulltext-loading">
              <LoadingSpinner size="sm" />
              {{ t('article.loadingFulltext') }}
            </div>

            <!-- HTML sanitizzato server-side con bleach -->
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div class="article-body" v-html="articleBody" />

            <div v-if="article.fulltext_status === 'failed'" class="fulltext-failed">
              {{ t('article.fulltextFailed') }}
            </div>

            <RelatedArticles
              :article-id="article.id"
              @article-click="openRelatedArticle"
            />
          </article>

        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { useRouter, useRoute, RouterLink } from 'vue-router'
import { articlesApi, type Article } from '@/api/articles'
import VoteButtons from '@/components/common/VoteButtons.vue'
import RelatedArticles from '@/components/common/RelatedArticles.vue'
import RelativeTime from '@/components/common/RelativeTime.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{ articleId: string | null }>()
const emit = defineEmits<{
  close: []
  'vote-changed': [vote: number, articleId: string]
}>()

const { t } = useI18n()
const router = useRouter()
const route = useRoute()

const article = ref<Article | null>(null)
const isLoading = ref(false)
let fulltextTimer: ReturnType<typeof setInterval> | null = null
let markReadTimer: ReturnType<typeof setTimeout> | null = null

const isOpen = computed(() => props.articleId !== null)

const articleBody = computed(() => {
  if (!article.value) return ''
  return article.value.content_fulltext || article.value.content_excerpt || ''
})

// Lock body scroll when drawer is open
watch(isOpen, (open) => {
  document.body.style.overflow = open ? 'hidden' : ''
}, { immediate: true })

watch(
  () => props.articleId,
  async (id) => {
    clearTimers()

    if (!id) {
      article.value = null
      return
    }

    isLoading.value = true
    try {
      const res = await articlesApi.get(id)
      article.value = res.data

      markReadTimer = setTimeout(async () => {
        if (article.value && !article.value.is_read) {
          await articlesApi.updateState(id, { is_read: true })
          if (article.value) article.value.is_read = true
        }
      }, 3000)

      if (res.data.fulltext_loading) {
        startFulltextPolling(id)
      }
    } catch {
      article.value = null
    } finally {
      isLoading.value = false
    }
  },
  { immediate: true },
)

function clearTimers() {
  if (fulltextTimer) { clearInterval(fulltextTimer); fulltextTimer = null }
  if (markReadTimer) { clearTimeout(markReadTimer); markReadTimer = null }
}

function close() {
  clearTimers()
  emit('close')
}

function startFulltextPolling(id: string) {
  let attempts = 0
  fulltextTimer = setInterval(async () => {
    attempts++
    if (attempts > 30) { clearInterval(fulltextTimer!); return }
    try {
      const res = await articlesApi.fulltextStatus(id)
      if (res.data.fulltext_available) {
        clearInterval(fulltextTimer!)
        const full = await articlesApi.get(id)
        if (article.value) {
          article.value.content_fulltext = full.data.content_fulltext
          article.value.fulltext_loading = false
          article.value.fulltext_status = full.data.fulltext_status
        }
      }
    } catch {
      clearInterval(fulltextTimer!)
    }
  }, 2000)
}

function onVoteChanged(vote: number, articleId: string) {
  if (article.value?.id === articleId) article.value.user_vote = vote
  emit('vote-changed', vote, articleId)
}

async function toggleStar() {
  if (!article.value) return
  const newVal = !article.value.is_starred
  article.value.is_starred = newVal
  await articlesApi.updateState(article.value.id, { is_starred: newVal })
}

function openRelatedArticle(related: Article) {
  router.replace({ query: { ...route.query, article: related.id } })
}

onUnmounted(() => {
  clearTimers()
  document.body.style.overflow = ''
})
</script>

<style scoped>
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 50;
  display: flex;
  justify-content: flex-end;
}
.drawer-panel {
  width: min(600px, 95vw);
  height: 100%;
  background: white;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 24px rgba(0, 0, 0, 0.15);
}
.drawer-header {
  position: sticky;
  top: 0;
  z-index: 1;
  background: white;
  border-bottom: 1px solid #e5e7eb;
  padding: 0.75rem 1rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.drawer-close {
  padding: 0.25rem 0.5rem;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  background: none;
  cursor: pointer;
  font-size: 1rem;
  flex-shrink: 0;
}
.drawer-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
  flex: 1;
}
.action-btn {
  padding: 0.25rem 0.5rem;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  background: none;
  cursor: pointer;
  font-size: 1rem;
  text-decoration: none;
  color: inherit;
  line-height: 1.4;
}
.action-btn:hover {
  background: #f3f4f6;
}
.open-reader-btn {
  margin-left: auto;
  font-size: 0.8rem;
  color: #2563eb;
  border-color: #2563eb;
}
.drawer-loading {
  display: flex;
  justify-content: center;
  padding: 2rem;
}
.drawer-content {
  padding: 1.5rem;
  flex: 1;
}
.article-meta {
  display: flex;
  gap: 0.4rem;
  align-items: center;
  font-size: 0.8rem;
  color: #6b7280;
  margin-bottom: 0.5rem;
  flex-wrap: wrap;
}
.feed-name {
  font-weight: 600;
  color: #2563eb;
}
.separator {
  color: #d1d5db;
}
.article-title {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 1.5rem;
  font-weight: 700;
  line-height: 1.3;
  margin: 0.75rem 0;
  color: #111827;
}
.article-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  margin-bottom: 1rem;
}
.tag {
  font-size: 0.7rem;
  background: #f3f4f6;
  color: #374151;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
}
.fulltext-loading {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #6b7280;
  margin-bottom: 1rem;
}
.fulltext-failed {
  font-size: 0.875rem;
  color: #d97706;
  margin-top: 1rem;
}
.article-body {
  font-size: 1rem;
  line-height: 1.7;
  color: #1f2937;
}
.article-body :deep(p) { margin-bottom: 1rem; }
.article-body :deep(a) {
  color: #2563eb;
  text-decoration: underline;
}
.article-body :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 4px;
}
.article-body :deep(h2),
.article-body :deep(h3) {
  font-weight: 700;
  margin: 1.25rem 0 0.5rem;
}

/* Slide-from-right animation */
.drawer-slide-enter-active {
  transition: background-color 0.3s ease;
}
.drawer-slide-leave-active {
  transition: background-color 0.3s ease;
}
.drawer-slide-enter-from,
.drawer-slide-leave-to {
  background-color: transparent;
}
.drawer-slide-enter-active .drawer-panel,
.drawer-slide-leave-active .drawer-panel {
  transition: transform 0.3s ease;
}
.drawer-slide-enter-from .drawer-panel,
.drawer-slide-leave-to .drawer-panel {
  transform: translateX(100%);
}
</style>
