<template>
  <article
    class="px-3 py-3 cursor-pointer border-l-2 transition-all"
    :class="[
      selected ? 'border-blue-500 bg-blue-50' : 'border-transparent hover:bg-gray-50',
      article.is_read ? 'opacity-60' : '',
    ]"
    @click="emit('select')"
  >
    <div class="flex items-start justify-between gap-2">
      <div class="flex items-center gap-1.5 min-w-0">
        <span
          class="w-2 h-2 rounded-full flex-shrink-0 mt-0.5"
          :class="article.is_read ? 'bg-transparent' : 'bg-blue-500'"
        />
        <span class="text-xs text-gray-500 truncate">
          {{ article.feed_title ?? '' }}
          <span v-if="article.published_at"> · {{ timeAgo(article.published_at) }}</span>
        </span>
      </div>

      <button
        class="flex-shrink-0 p-0.5 rounded transition-colors hover:text-yellow-500"
        :class="article.is_starred ? 'text-yellow-400' : 'text-gray-300'"
        :aria-label="article.is_starred ? t('article.unstar') : t('article.star')"
        @click.stop="emit('toggleStar')"
      >
        <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      </button>
    </div>

    <h3
      class="mt-1 text-sm font-semibold leading-snug line-clamp-2"
      :class="article.is_read ? 'text-gray-500' : 'text-gray-900'"
    >
      {{ article.title ?? t('common.noResults') }}
    </h3>

    <p v-if="article.content_excerpt" class="mt-1 text-xs text-gray-500 line-clamp-2" v-html="stripTags(article.content_excerpt)" />

    <div v-if="article.tags.length > 0" class="mt-1.5 flex flex-wrap gap-1">
      <span
        v-for="tag in article.tags.slice(0, 4)"
        :key="tag"
        class="text-[10px] px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded"
      >
        {{ tag }}
      </span>
    </div>
  </article>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { Article } from '@/api/articles'

defineProps<{
  article: Article
  selected: boolean
}>()

const emit = defineEmits<{
  select: []
  toggleStar: []
}>()

const { t } = useI18n()

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h`
  return `${Math.floor(hours / 24)}d`
}

function stripTags(html: string): string {
  return html.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
}
</script>
