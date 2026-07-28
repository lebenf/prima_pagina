<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="flex h-full overflow-hidden">
    <!-- Feed list — left panel -->
    <aside
      class="w-[200px] flex-shrink-0 border-r border-gray-200 bg-gray-50 overflow-hidden"
      :class="mobile && mobilePanel !== 'feeds' ? 'hidden' : ''"
    >
      <FeedList />
    </aside>

    <!-- Article list — center panel -->
    <section
      class="w-[350px] flex-shrink-0 overflow-hidden"
      :class="mobile && mobilePanel !== 'list' ? 'hidden' : ''"
    >
      <ArticleList />
    </section>

    <!-- Article reader — right panel -->
    <main
      class="flex-1 overflow-hidden"
      :class="mobile && mobilePanel !== 'reader' ? 'hidden' : ''"
    >
      <ArticleReader
        :article="articlesStore.selectedArticle"
        :show-back="mobile"
        @back="mobilePanel = 'list'"
        @select-article="articlesStore.selectArticle($event)"
      />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import { useWindowSize } from '@vueuse/core'
import { useRoute } from 'vue-router'
import { useFeedsStore } from '@/stores/feeds'
import { useArticlesStore } from '@/stores/articles'
import { articlesApi } from '@/api/articles'
import { useReaderKeyboard } from '@/composables/useKeyboardNavigation'
import FeedList from '@/components/reader/FeedList.vue'
import ArticleList from '@/components/reader/ArticleList.vue'
import ArticleReader from '@/components/reader/ArticleReader.vue'

const route = useRoute()
const feedsStore = useFeedsStore()
const articlesStore = useArticlesStore()
const { width } = useWindowSize()
const mobile = computed(() => width.value < 768)
type Panel = 'feeds' | 'list' | 'reader'
const mobilePanel = ref<Panel>('list')

useReaderKeyboard(articlesStore, () => {
  if (mobile.value) mobilePanel.value = 'list'
})

async function applyArticleFromQuery() {
  const articleId = route.query.article as string | undefined
  if (!articleId || articleId === articlesStore.selectedArticleId) return
  try {
    const res = await articlesApi.get(articleId)
    articlesStore.selectArticle(res.data)
    if (mobile.value) mobilePanel.value = 'reader'
  } catch {
    // article not found or unauthorized — ignore
  }
}

onMounted(async () => {
  await feedsStore.loadSubscribed()
  await articlesStore.loadForFeed(null)   // resets selectedArticleId first
  await applyArticleFromQuery()            // then applies ?article= if present — sequential, no race
})

// Only fires for CHANGES after mount (e.g. a second SearchModal click while
// already in Reader) — Vue Router reuses this component instance across
// reader-family navigations, so onMounted does not re-fire. onMounted above
// already handled the initial value, so this is deliberately not
// `immediate: true` (that would race loadForFeed's async reset of
// selectedArticleId, since an immediate watcher fires during setup, before
// onMounted).
watch(() => route.query.article, applyArticleFromQuery)

// When user selects a feed, reload articles
watch(
  () => feedsStore.selectedFeedId,
  (feedId) => {
    articlesStore.loadForFeed(feedId)
    if (mobile.value) mobilePanel.value = 'list'
  },
)

// When user selects an article: fetch full detail (triggers fulltext), switch panel, mark-as-read
let markReadTimer: ReturnType<typeof setTimeout> | null = null

watch(
  () => articlesStore.selectedArticleId,
  async (id) => {
    if (markReadTimer) { clearTimeout(markReadTimer); markReadTimer = null }
    if (id) {
      if (mobile.value) mobilePanel.value = 'reader'
      // Fetch ArticleDetail so the backend triggers fulltext enrichment
      // and the reader gets fulltext_loading/fulltext_status
      try {
        const res = await articlesApi.get(id)
        articlesStore.updateArticle(res.data)
      } catch { /* ignore */ }
      markReadTimer = setTimeout(() => {
        articlesStore.markRead(id)
        markReadTimer = null
      }, 3000)
    }
  },
)

// Reload articles when filters change (setFilter already resets page to 1)
watch(
  () => articlesStore.filters,
  () => { articlesStore.load(articlesStore.currentFeedId) },
  { deep: true },
)
</script>
