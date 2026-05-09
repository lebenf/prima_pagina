<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <nav class="nav">
    <RouterLink
      :to="{ name: 'frontpage' }"
      class="nav-item"
      :class="{ collapsed }"
      active-class="active"
    >
      <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
        <path d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
      </svg>
      <span v-if="!collapsed" class="nav-label">{{ t('nav.frontpage') }}</span>
    </RouterLink>

    <RouterLink
      :to="{ name: 'reader' }"
      class="nav-item"
      :class="{ collapsed }"
      active-class="active"
    >
      <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
        <path d="M4 6h16M4 10h16M4 14h16M4 18h16" />
      </svg>
      <span v-if="!collapsed" class="nav-label">{{ t('nav.reader') }}</span>
    </RouterLink>
  </nav>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'

defineProps<{ collapsed: boolean }>()

const { t } = useI18n()
</script>

<style scoped>
.nav {
  padding: var(--bbf-s-2);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--bbf-s-3);
  padding: 8px var(--bbf-s-3);
  border-radius: var(--bbf-r-md);
  color: var(--bbf-ink-2);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: background 0.12s, color 0.12s;
  white-space: nowrap;
}
.nav-item:hover { background: var(--bbf-surface-2); color: var(--bbf-ink); }
.nav-item.active { background: var(--bbf-primary-soft); color: var(--bbf-primary-ink); }
.nav-item.collapsed { justify-content: center; padding: 8px; }

.nav-label { flex: 1; }
</style>
