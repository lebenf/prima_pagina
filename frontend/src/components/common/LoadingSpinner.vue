<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="flex items-center justify-center" :class="containerClass">
    <svg
      class="animate-spin"
      :style="{ color: 'var(--bbf-primary)' }"
      :class="sizeClass"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
      <path
        class="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
    <span v-if="label" class="ml-2 text-sm text-gray-500">{{ label }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    size?: 'sm' | 'md' | 'lg'
    label?: string
    fullscreen?: boolean
  }>(),
  { size: 'md' }
)

const sizeClass = computed(() => ({
  'w-4 h-4': props.size === 'sm',
  'w-8 h-8': props.size === 'md',
  'w-12 h-12': props.size === 'lg',
}))

const containerClass = computed(() =>
  props.fullscreen ? 'fixed inset-0 bg-white/80 z-50' : 'p-4'
)
</script>
