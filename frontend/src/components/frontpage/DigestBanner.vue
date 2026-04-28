<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div
    v-if="digest.status === 'failed'"
    class="digest-banner flex items-center gap-3 px-4 py-3 mb-4 rounded"
    style="background: #fef2f2; border: 1px solid #fca5a5;"
  >
    <span class="text-xl flex-shrink-0">⚠️</span>
    <div class="flex-1 min-w-0">
      <p class="font-semibold text-red-700 text-sm">{{ t('digest.generationFailed') }}</p>
      <p v-if="digest.generation_error" class="text-xs text-red-500 mt-0.5 truncate">{{ digest.generation_error }}</p>
    </div>
    <button
      @click="$emit('retry')"
      class="text-sm font-medium text-red-700 hover:underline whitespace-nowrap flex-shrink-0"
    >{{ t('digest.retry') }}</button>
    <button
      @click="$emit('dismiss')"
      class="text-gray-400 hover:text-gray-700 flex-shrink-0 text-lg leading-none"
      :aria-label="t('common.cancel')"
    >×</button>
  </div>

  <div
    v-else
    class="digest-banner flex items-center gap-3 px-4 py-3 mb-4 rounded"
    style="background: #fdf8e1; border: 1px solid #e8d87a;"
  >
    <span class="text-xl flex-shrink-0">📰</span>
    <div class="flex-1 min-w-0">
      <p class="font-semibold text-gray-800 text-sm">
        {{ digest.title || t('frontpage.latestDigest') }}
      </p>
      <p class="text-xs text-gray-500 mt-0.5">
        {{ t('frontpage.digestArticles', { count: digest.article_count }) }}
        <span v-if="digest.llm_provider"> · {{ t('frontpage.digestGenerated', { provider: digest.llm_provider }) }}</span>
      </p>
    </div>
    <button
      @click="$emit('open')"
      class="text-sm font-medium text-blue-700 hover:underline whitespace-nowrap flex-shrink-0"
    >{{ t('frontpage.readDigest') }} →</button>
    <button
      @click="$emit('dismiss')"
      class="text-gray-400 hover:text-gray-700 flex-shrink-0 text-lg leading-none"
      :aria-label="t('common.cancel')"
    >×</button>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { Digest } from '@/api/digest'

defineProps<{ digest: Digest }>()
defineEmits<{ dismiss: []; open: []; retry: [] }>()
const { t } = useI18n()
</script>
