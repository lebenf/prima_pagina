<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div v-if="digest.status === 'failed'" class="digest-content">
    <div class="error-section">
      <p class="error-heading">⚠️ {{ t('digest.generationFailed') }}</p>
      <p v-if="digest.generation_error" class="error-detail">{{ digest.generation_error }}</p>
      <p class="error-hint">{{ t('digest.generationFailedHint') }}</p>
    </div>
  </div>

  <div
    v-else
    class="digest-content prose prose-sm max-w-none"
    v-html="digest.content_html || ''"
  />
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { Digest } from '@/api/digest'

defineProps<{ digest: Digest }>()
const { t } = useI18n()
</script>

<style scoped>
.digest-content :deep(h2) {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 1.25rem;
  font-weight: 700;
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid #e5e7eb;
}
.digest-content :deep(h3) {
  font-size: 1rem;
  font-weight: 600;
  margin-top: 1rem;
  margin-bottom: 0.5rem;
}
.digest-content :deep(p) {
  margin-bottom: 0.75rem;
  line-height: 1.6;
  color: #374151;
}
.digest-content :deep(a) {
  color: #1d4ed8;
  text-decoration: underline;
}
.digest-content :deep(blockquote) {
  border-left: 3px solid #d1d5db;
  padding-left: 1rem;
  color: #6b7280;
  font-style: italic;
  margin: 0.75rem 0;
}
.digest-content :deep(article) {
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
