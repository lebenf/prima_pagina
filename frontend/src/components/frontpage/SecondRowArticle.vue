<template>
  <article class="second-row-article cursor-pointer hover:bg-gray-50 transition-colors" @click="$emit('click')">
    <span v-if="article.tags?.length" class="text-xs font-bold uppercase tracking-widest text-gray-500 mb-1 block">
      {{ article.tags[0] }}
    </span>
    <h3 class="font-serif text-lg font-bold leading-snug mb-2" style="font-family: Georgia, 'Times New Roman', serif;">
      {{ article.title }}
    </h3>
    <p v-if="plainExcerpt" class="text-sm text-gray-600 leading-relaxed line-clamp-2 mb-2">
      {{ plainExcerpt }}
    </p>
    <footer class="flex items-center gap-1 text-xs text-gray-400">
      <span v-if="article.feed_title">{{ article.feed_title }}</span>
      <span v-if="article.feed_title">·</span>
      <RelativeTime :date="article.published_at" />
    </footer>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import RelativeTime from '@/components/common/RelativeTime.vue'
import type { Article } from '@/api/articles'

const props = defineProps<{ article: Article }>()
defineEmits<{ click: [] }>()

const plainExcerpt = computed(() => {
  if (!props.article.content_excerpt) return ''
  const div = document.createElement('div')
  div.innerHTML = props.article.content_excerpt
  return div.textContent || div.innerText || ''
})
</script>
