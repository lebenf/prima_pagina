<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="flex gap-1 px-3 py-2 border-b border-gray-200 bg-white">
    <button
      v-for="f in filterOptions"
      :key="f.key"
      class="px-3 py-1 text-sm rounded-full transition-colors"
      :class="active === f.key
        ? 'bg-blue-600 text-white'
        : 'text-gray-600 hover:bg-gray-100'"
      @click="select(f.key)"
    >
      {{ f.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useArticlesStore } from '@/stores/articles'

const { t } = useI18n()
const articlesStore = useArticlesStore()

type FilterKey = 'all' | 'unread' | 'starred'

const filterOptions = computed(() => [
  { key: 'all' as FilterKey, label: t('reader.all') },
  { key: 'unread' as FilterKey, label: t('reader.unread') },
  { key: 'starred' as FilterKey, label: t('reader.starred') },
])

const active = computed<FilterKey>(() => {
  if (articlesStore.filters.is_starred) return 'starred'
  if (articlesStore.filters.is_read === false) return 'unread'
  return 'all'
})

function select(key: FilterKey) {
  if (key === 'all') {
    articlesStore.setFilter('is_read', undefined)
    articlesStore.setFilter('is_starred', undefined)
  } else if (key === 'unread') {
    articlesStore.setFilter('is_read', false)
    articlesStore.setFilter('is_starred', undefined)
  } else {
    articlesStore.setFilter('is_read', undefined)
    articlesStore.setFilter('is_starred', true)
  }
}
</script>
