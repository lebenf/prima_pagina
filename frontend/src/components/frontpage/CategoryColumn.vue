<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="category-column">
    <header class="category-header mb-3 pb-1 border-b-2" :style="{ borderColor: headerColor }">
      <h3 class="text-xs font-black uppercase tracking-widest" :style="{ color: headerColor }">
        {{ column.category_name }}
      </h3>
    </header>
    <ul class="space-y-3">
      <li
        v-for="article in column.articles"
        :key="article.id"
        class="cursor-pointer hover:bg-gray-50 transition-colors pb-3 border-b border-gray-200 last:border-0 last:pb-0"
        @click="$emit('article-click', article)"
      >
        <p class="font-serif text-sm font-bold leading-snug mb-1 hover:underline" style="font-family: Georgia, 'Times New Roman', serif;">
          {{ article.title }}
        </p>
        <div class="flex items-center gap-1 text-xs text-gray-400">
          <span v-if="article.feed_title">{{ article.feed_title }}</span>
          <span v-if="article.feed_title">·</span>
          <RelativeTime :date="article.published_at" />
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import RelativeTime from '@/components/common/RelativeTime.vue'
import type { Article } from '@/api/articles'

interface Column {
  category_slug: string
  category_name: string
  articles: Article[]
}

const props = defineProps<{ column: Column }>()
defineEmits<{ 'article-click': [article: Article] }>()

const headerColor = computed(() => {
  const hue = props.column.category_slug
    .split('')
    .reduce((acc, c) => acc + c.charCodeAt(0), 0) % 360
  return `hsl(${hue}, 60%, 35%)`
})
</script>
