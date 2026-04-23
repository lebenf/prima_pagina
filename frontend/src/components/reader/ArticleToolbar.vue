<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="flex items-center gap-1 px-4 py-2 border-b border-gray-200 bg-white">
    <button
      v-if="showBack"
      class="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900 mr-2"
      @click="emit('back')"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
      {{ t('reader.back') }}
    </button>

    <div class="flex-1" />

    <button
      class="p-1.5 rounded transition-colors hover:bg-gray-100"
      :class="article.is_starred ? 'text-yellow-400' : 'text-gray-400 hover:text-yellow-500'"
      :title="article.is_starred ? t('article.unstar') : t('article.star')"
      @click="articlesStore.toggleStar(article.id)"
    >
      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
      </svg>
    </button>

    <button
      v-if="article.url"
      class="p-1.5 rounded text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
      :title="t('reader.openOriginal')"
      @click="openOriginal"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
      </svg>
    </button>

    <button
      class="p-1.5 rounded text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
      :title="article.is_read ? t('article.markUnread') : t('article.markRead')"
      @click="articlesStore.toggleRead(article.id)"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path v-if="article.is_read" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        <path v-else stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
      </svg>
    </button>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useArticlesStore } from '@/stores/articles'
import type { Article } from '@/api/articles'

const props = defineProps<{
  article: Article
  showBack?: boolean
}>()

const emit = defineEmits<{
  back: []
}>()

const { t } = useI18n()
const articlesStore = useArticlesStore()

function openOriginal() {
  if (props.article.url) window.open(props.article.url, '_blank', 'noopener,noreferrer')
}
</script>
