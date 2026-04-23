<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <button
    class="w-full flex items-center gap-2 px-3 py-2 text-left rounded-md transition-colors"
    :class="selected ? 'bg-blue-50 text-blue-700' : 'hover:bg-gray-100 text-gray-700'"
    @click="emit('select')"
  >
    <img
      v-if="feed.favicon_url && !faviconError"
      :src="feed.favicon_url"
      class="w-4 h-4 rounded-sm flex-shrink-0 object-contain"
      @error="faviconError = true"
    />
    <span
      v-else
      class="w-4 h-4 rounded-sm flex-shrink-0 flex items-center justify-center text-white text-[9px] font-bold"
      :style="{ backgroundColor: colorForTitle(displayTitle) }"
    >
      {{ displayTitle.charAt(0).toUpperCase() }}
    </span>

    <span class="flex-1 truncate text-sm">{{ displayTitle }}</span>

    <span
      v-if="feed.unread_count > 0"
      class="flex-shrink-0 text-xs font-medium px-1.5 py-0.5 rounded-full"
      :class="selected ? 'bg-blue-200 text-blue-800' : 'bg-gray-200 text-gray-600'"
    >
      {{ feed.unread_count > 99 ? '99+' : feed.unread_count }}
    </span>
  </button>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { Feed } from '@/api/feeds'

interface FeedWithCount extends Feed {
  unread_count: number
}

const props = defineProps<{
  feed: FeedWithCount
  selected: boolean
}>()

const emit = defineEmits<{
  select: []
}>()

const faviconError = ref(false)

const displayTitle = computed(() => props.feed.custom_name ?? props.feed.title ?? '?')

function colorForTitle(title: string): string {
  let hash = 0
  for (const ch of title) hash = ch.charCodeAt(0) + ((hash << 5) - hash)
  const hue = Math.abs(hash) % 360
  return `hsl(${hue}, 55%, 45%)`
}
</script>
