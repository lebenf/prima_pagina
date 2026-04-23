<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="flex flex-col h-full overflow-hidden border-r border-gray-200">
    <ReaderFilters />

    <div class="flex-1 overflow-y-auto divide-y divide-gray-100" @scroll="onScroll">
      <template v-if="articlesStore.isLoading && articlesStore.articles.length === 0">
        <div class="flex items-center justify-center py-12">
          <div class="w-6 h-6 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
        </div>
      </template>

      <template v-else-if="articlesStore.articles.length === 0">
        <p class="px-4 py-8 text-center text-sm text-gray-400">{{ t('reader.noArticles') }}</p>
      </template>

      <template v-else>
        <ArticleListItem
          v-for="article in articlesStore.articles"
          :key="article.id"
          :article="article"
          :selected="articlesStore.selectedArticleId === article.id"
          @select="articlesStore.selectedArticleId = article.id"
          @toggle-star="articlesStore.toggleStar(article.id)"
        />

        <InfiniteScroll
          :loading="articlesStore.isLoading"
          :has-more="articlesStore.pagination.page < articlesStore.pagination.pages"
          @load-more="articlesStore.loadNextPage()"
        />
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useArticlesStore } from '@/stores/articles'
import ReaderFilters from './ReaderFilters.vue'
import ArticleListItem from './ArticleListItem.vue'
import InfiniteScroll from '@/components/common/InfiniteScroll.vue'

const { t } = useI18n()
const articlesStore = useArticlesStore()

function onScroll() {
  // Handled by InfiniteScroll sentinel
}
</script>
