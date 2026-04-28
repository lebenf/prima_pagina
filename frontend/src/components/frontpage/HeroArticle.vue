<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <article class="hero-article cursor-pointer border-b-2 border-gray-800 pb-4 mb-4" @click="$emit('click')">
    <div class="flex gap-4">
      <div class="hero-content flex-1">
        <span v-if="article.tags?.length" class="category-label text-xs font-bold uppercase tracking-widest text-gray-500 mb-2 block">
          {{ article.tags[0] }}
        </span>
        <h2 class="hero-title font-serif text-4xl md:text-5xl font-black leading-tight mb-3" style="font-family: Georgia, 'Times New Roman', serif;">
          {{ article.title }}
        </h2>
        <p v-if="plainExcerpt" class="hero-excerpt text-gray-700 text-base leading-relaxed mb-3 line-clamp-3">
          {{ plainExcerpt }}
        </p>
        <footer class="hero-meta flex items-center gap-2 text-sm text-gray-500">
          <span v-if="article.feed_title" class="feed-name font-medium">{{ article.feed_title }}</span>
          <span v-if="article.feed_title" class="separator">·</span>
          <RelativeTime :date="article.published_at" />
          <div class="hero-actions ml-auto flex items-center gap-2">
            <VoteButtons
              :article-id="article.id"
              :initial-vote="article.user_vote ?? 0"
              :compact="true"
              @vote-changed="(vote, id) => $emit('vote-changed', vote, id)"
            />
            <button
              @click.stop="$emit('toggle-star')"
              class="action-btn text-lg hover:text-yellow-500 transition-colors"
              :class="article.is_starred ? 'text-yellow-500' : 'text-gray-400'"
            >{{ article.is_starred ? '★' : '☆' }}</button>
            <button
              @click.stop="$emit('click')"
              class="read-btn text-sm font-medium text-blue-700 hover:underline"
            >{{ t('article.readMore') }} →</button>
          </div>
        </footer>
      </div>
      <div v-if="heroImage" class="hero-image w-48 h-36 flex-shrink-0 hidden md:block overflow-hidden rounded">
        <img :src="heroImage" :alt="article.title || ''" loading="lazy" class="w-full h-full object-cover" />
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import RelativeTime from '@/components/common/RelativeTime.vue'
import VoteButtons from '@/components/common/VoteButtons.vue'
import type { Article } from '@/api/articles'

const props = defineProps<{ article: Article }>()
defineEmits<{ click: []; 'toggle-star': []; 'mark-read': []; 'vote-changed': [vote: number, articleId: string] }>()
const { t } = useI18n()

const plainExcerpt = computed(() => {
  if (!props.article.content_excerpt) return ''
  const div = document.createElement('div')
  div.innerHTML = props.article.content_excerpt
  return div.textContent || div.innerText || ''
})

const heroImage = computed(() => {
  if (!props.article.content_excerpt) return null
  const parser = new DOMParser()
  const doc = parser.parseFromString(props.article.content_excerpt, 'text/html')
  const img = doc.querySelector('img')
  return img?.src || null
})
</script>
