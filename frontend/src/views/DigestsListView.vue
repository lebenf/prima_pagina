<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="digests-view max-w-3xl mx-auto px-4 py-6">
    <h1 class="digests-view__title">{{ t('digest.title') }}</h1>

    <template v-if="digestsStore.isLoading && digestsStore.digests.length === 0">
      <div class="flex items-center justify-center py-12">
        <div class="w-6 h-6 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
      </div>
    </template>

    <template v-else-if="digestsStore.digests.length === 0">
      <p class="px-4 py-8 text-center text-sm text-gray-400">{{ t('digest.noDigest') }}</p>
    </template>

    <template v-else>
      <ul class="digests-view__list">
        <li v-for="digest in digestsStore.digests" :key="digest.id">
          <button
            class="digest-row"
            @click="router.push({ name: 'digest', params: { id: digest.id } })"
          >
            <div class="digest-row__main">
              <h2 class="digest-row__title">{{ digest.title || t('digest.title') }}</h2>
              <p class="digest-row__meta">
                {{ t('digest.period', { start: formatDate(digest.period_start), end: formatDate(digest.period_end) }) }}
              </p>
              <p v-if="digest.status === 'failed'" class="digest-row__error">
                {{ t('digest.generationFailed') }}
              </p>
              <p v-else class="digest-row__meta">
                {{ t('digest.articles', { count: digest.article_count }) }}
                <span v-if="digest.llm_provider"> · {{ t('digest.provider', { provider: digest.llm_provider }) }}</span>
              </p>
            </div>
          </button>
        </li>
      </ul>

      <InfiniteScroll
        :loading="digestsStore.isLoading"
        :has-more="digestsStore.pagination.page < digestsStore.pagination.pages"
        @load-more="digestsStore.loadNextPage()"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useDigestsStore } from '@/stores/digests'
import InfiniteScroll from '@/components/common/InfiniteScroll.vue'

const { t, locale } = useI18n()
const router = useRouter()
const digestsStore = useDigestsStore()

function formatDate(iso: string) {
  return new Intl.DateTimeFormat(locale.value, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(iso))
}

onMounted(() => digestsStore.load())
</script>

<style scoped>
.digests-view__title {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 1.75rem;
  font-weight: 900;
  margin-bottom: 1.25rem;
}
.digests-view__list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}
.digests-view__list li {
  padding-bottom: 1.25rem;
  border-bottom: 1px solid #e5e7eb;
}
.digests-view__list li:last-child {
  border-bottom: none;
}
.digest-row {
  display: block;
  width: 100%;
  text-align: left;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
}
.digest-row__title {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 1.1rem;
  font-weight: 700;
  margin: 0 0 0.25rem;
  color: #111827;
}
.digest-row__meta {
  font-size: 0.85rem;
  color: #6b7280;
  margin: 0.15rem 0;
}
.digest-row__error {
  font-size: 0.85rem;
  color: #dc2626;
  margin: 0.15rem 0;
  font-weight: 600;
}
</style>
