<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <teleport to="body">
    <div class="modal-backdrop fixed inset-0 bg-black bg-opacity-50 z-50 flex items-start justify-center p-4 md:p-8" @click.self="$emit('close')">
      <div class="modal-container bg-white rounded-lg shadow-2xl w-full max-w-3xl max-h-screen flex flex-col">
        <!-- Header -->
        <div class="modal-header flex items-start justify-between p-6 border-b border-gray-200 flex-shrink-0">
          <div>
            <h2 class="font-serif text-2xl font-bold" style="font-family: Georgia, 'Times New Roman', serif;">
              {{ digest?.title || t('frontpage.latestDigest') }}
            </h2>
            <p class="text-sm text-gray-500 mt-1">
              {{ t('frontpage.digestArticles', { count: digest?.article_count || 0 }) }}
              <span v-if="digest?.llm_provider"> · {{ t('frontpage.digestGenerated', { provider: digest.llm_provider }) }}</span>
            </p>
          </div>
          <button
            @click="$emit('close')"
            class="text-gray-400 hover:text-gray-700 text-2xl leading-none ml-4 flex-shrink-0"
            :aria-label="t('common.cancel')"
          >×</button>
        </div>

        <!-- Error state -->
        <div v-if="digest?.status === 'failed'" class="modal-body overflow-y-auto flex-1 p-6">
          <div class="error-section">
            <p class="error-heading">⚠️ {{ t('digest.generationFailed') }}</p>
            <p v-if="digest.generation_error" class="error-detail">{{ digest.generation_error }}</p>
            <p class="error-hint">{{ t('digest.generationFailedHint') }}</p>
          </div>
        </div>

        <!-- Content — server-sanitized HTML -->
        <div
          v-else
          class="modal-body overflow-y-auto flex-1 p-6 prose prose-sm max-w-none"
          v-html="digest?.content_html || ''"
        />
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Digest } from '@/api/digest'

defineProps<{ digest: Digest | null }>()
defineEmits<{ close: [] }>()
const { t } = useI18n()

onMounted(() => { document.body.style.overflow = 'hidden' })
onUnmounted(() => { document.body.style.overflow = '' })
</script>

<style scoped>
/* Digest content typography */
.modal-body :deep(h2) {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 1.25rem;
  font-weight: 700;
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid #e5e7eb;
}
.modal-body :deep(h3) {
  font-size: 1rem;
  font-weight: 600;
  margin-top: 1rem;
  margin-bottom: 0.5rem;
}
.modal-body :deep(p) {
  margin-bottom: 0.75rem;
  line-height: 1.6;
  color: #374151;
}
.modal-body :deep(a) {
  color: #1d4ed8;
  text-decoration: underline;
}
.modal-body :deep(blockquote) {
  border-left: 3px solid #d1d5db;
  padding-left: 1rem;
  color: #6b7280;
  font-style: italic;
  margin: 0.75rem 0;
}
.modal-body :deep(article) {
  border-top: 1px solid #f3f4f6;
  padding-top: 1rem;
  margin-top: 1rem;
}
.error-section {
  background: #fef2f2;
  border: 1px solid #fca5a5;
  border-radius: 6px;
  padding: 1.25rem 1.5rem;
}
.error-heading {
  font-weight: 700;
  color: #dc2626;
  margin-bottom: 0.5rem;
}
.error-detail {
  font-size: 0.875rem;
  color: #6b7280;
  margin-bottom: 0.75rem;
  font-family: monospace;
  word-break: break-all;
}
.error-hint {
  font-size: 0.875rem;
  color: #9ca3af;
}
</style>
