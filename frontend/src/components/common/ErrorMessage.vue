<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
    <svg class="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
    <div class="flex-1">
      <p class="text-sm font-medium">{{ message || t('common.error') }}</p>
      <button
        v-if="retryable"
        class="mt-2 text-xs underline hover:no-underline"
        @click="emit('retry')"
      >
        {{ t('common.retry') }}
      </button>
    </div>
    <button v-if="dismissible" class="text-red-400 hover:text-red-600" @click="emit('dismiss')">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
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

const emit = defineEmits<{
  retry: []
  dismiss: []
}>()

const { t } = useI18n()
</script>
