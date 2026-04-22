<template>
  <div class="digest-banner flex items-center gap-3 px-4 py-3 mb-4 rounded" style="background: #fdf8e1; border: 1px solid #e8d87a;">
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
defineEmits<{ dismiss: []; open: [] }>()
const { t } = useI18n()
</script>
