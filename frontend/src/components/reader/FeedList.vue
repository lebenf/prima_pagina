<template>
  <nav class="flex flex-col h-full overflow-y-auto py-2">
    <!-- All feeds -->
    <FeedItem
      :feed="allFeedsItem"
      :selected="feedsStore.selectedFeedId === null"
      @select="feedsStore.selectedFeedId = null"
    />

    <div class="mt-1 border-t border-gray-200 pt-1">
      <template v-if="feedsStore.isLoading && feedsStore.feeds.length === 0">
        <p class="px-3 py-2 text-xs text-gray-400">{{ t('common.loading') }}</p>
      </template>

      <template v-else-if="sortedFeeds.length === 0">
        <p class="px-3 py-2 text-xs text-gray-400">{{ t('feed.noFeeds') }}</p>
      </template>

      <template v-else>
        <!-- Uncategorized feeds -->
        <FeedItem
          v-for="feed in uncategorized"
          :key="feed.id"
          :feed="feed"
          :selected="feedsStore.selectedFeedId === feed.id"
          @select="feedsStore.selectedFeedId = feed.id"
        />

        <!-- Categorized groups -->
        <template v-for="(group, catId) in categorized" :key="catId">
          <p class="px-3 pt-3 pb-1 text-[10px] font-semibold uppercase tracking-wider text-gray-400 truncate">
            {{ catId }}
          </p>
          <FeedItem
            v-for="feed in group"
            :key="feed.id"
            :feed="feed"
            :selected="feedsStore.selectedFeedId === feed.id"
            @select="feedsStore.selectedFeedId = feed.id"
          />
        </template>
      </template>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFeedsStore } from '@/stores/feeds'
import FeedItem from './FeedItem.vue'

const { t } = useI18n()
const feedsStore = useFeedsStore()

const allFeedsItem = computed(() => ({
  id: '__all__',
  title: t('reader.allFeeds'),
  custom_name: undefined,
  site_url: null,
  favicon_url: null,
  category_id: null,
  language: null,
  last_fetched_at: null,
  is_active: true,
  is_subscribed: true,
  unread_count: feedsStore.totalUnread,
}))

const sortedFeeds = computed(() =>
  [...feedsStore.feedsWithCounts].sort((a, b) => {
    const ua = feedsStore.unreadCounts[a.id] ?? 0
    const ub = feedsStore.unreadCounts[b.id] ?? 0
    if (ub !== ua) return ub - ua
    return (a.title ?? '').localeCompare(b.title ?? '')
  })
)

const uncategorized = computed(() =>
  sortedFeeds.value.filter(f => !f.category_id)
)

const categorized = computed(() => {
  const groups: Record<string, typeof sortedFeeds.value> = {}
  for (const feed of sortedFeeds.value) {
    if (!feed.category_id) continue
    if (!groups[feed.category_id]) groups[feed.category_id] = []
    groups[feed.category_id].push(feed)
  }
  return groups
})
</script>
