<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <nav class="flex-1 pt-2">
    <RouterLink
      :to="{ name: 'frontpage' }"
      class="flex items-center gap-3 px-4 py-3 hover:bg-primary-700 transition-colors"
      :class="{ 'justify-center': collapsed }"
      active-class="bg-primary-600"
    >
      <!-- Newspaper icon -->
      <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
      </svg>
      <span v-if="!collapsed" class="text-sm font-medium">{{ t('nav.frontpage') }}</span>
    </RouterLink>

    <RouterLink
      :to="{ name: 'reader' }"
      class="flex items-center gap-3 px-4 py-3 hover:bg-primary-700 transition-colors"
      :class="{ 'justify-center': collapsed }"
      active-class="bg-primary-600"
    >
      <!-- List icon -->
      <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
      </svg>
      <span v-if="!collapsed" class="text-sm">{{ t('nav.reader') }}</span>
    </RouterLink>
  </nav>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'

defineProps<{ collapsed: boolean }>()

const { t } = useI18n()
</script>
