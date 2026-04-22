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
      />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import { useWindowSize } from '@vueuse/core'
import { useFeedsStore } from '@/stores/feeds'
import { useArticlesStore } from '@/stores/articles'
import { useReaderKeyboard } from '@/composables/useKeyboardNavigation'
import FeedList from '@/components/reader/FeedList.vue'
import ArticleList from '@/components/reader/ArticleList.vue'
import ArticleReader from '@/components/reader/ArticleReader.vue'

const feedsStore = useFeedsStore()
const articlesStore = useArticlesStore()
const { width } = useWindowSize()
const mobile = computed(() => width.value < 768)
type Panel = 'feeds' | 'list' | 'reader'
const mobilePanel = ref<Panel>('list')

useReaderKeyboard(articlesStore, () => {
  if (mobile.value) mobilePanel.value = 'list'
})

onMounted(async () => {
  await feedsStore.loadSubscribed()
  await articlesStore.loadForFeed(null)
})

// When user selects a feed, reload articles
watch(
  () => feedsStore.selectedFeedId,
  (feedId) => {
    articlesStore.loadForFeed(feedId)
    if (mobile.value) mobilePanel.value = 'list'
  },
)

// When user selects an article: switch to reader panel on mobile + mark-as-read after 3s
let markReadTimer: ReturnType<typeof setTimeout> | null = null

watch(
  () => articlesStore.selectedArticleId,
  (id) => {
    if (markReadTimer) { clearTimeout(markReadTimer); markReadTimer = null }
    if (id) {
      if (mobile.value) mobilePanel.value = 'reader'
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
