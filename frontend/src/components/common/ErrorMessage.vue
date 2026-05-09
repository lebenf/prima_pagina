<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="error-msg">
    <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24" class="error-icon">
      <path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
    <div class="error-body">
      <p class="error-text">{{ message || t('common.error') }}</p>
      <button v-if="retryable" class="error-retry" @click="emit('retry')">
        {{ t('common.retry') }}
      </button>
    </div>
    <button v-if="dismissible" class="error-dismiss" @click="emit('dismiss')">
      <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

defineProps<{
  message?: string
  retryable?: boolean
  dismissible?: boolean
}>()

const emit = defineEmits<{ retry: []; dismiss: [] }>()
const { t } = useI18n()
</script>

<style scoped>
.error-msg {
  display: flex;
  align-items: flex-start;
  gap: var(--bbf-s-3);
  border-radius: var(--bbf-r-md);
  border: 1px solid var(--bbf-danger);
  background: var(--bbf-danger-soft);
  padding: var(--bbf-s-4);
  color: var(--bbf-danger);
}
.error-icon { flex-shrink: 0; margin-top: 1px; }
.error-body { flex: 1; }
.error-text { font-size: 14px; font-weight: 500; margin: 0; }
.error-retry {
  margin-top: 6px;
  font-size: 12px;
  color: var(--bbf-danger);
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  text-decoration: underline;
  font-family: var(--bbf-font);
}
.error-retry:hover { text-decoration: none; }
.error-dismiss {
  color: var(--bbf-danger);
  background: none;
  border: none;
  padding: 2px;
  cursor: pointer;
  opacity: 0.6;
  transition: opacity 0.15s;
}
.error-dismiss:hover { opacity: 1; }
</style>
