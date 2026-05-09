<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <nav class="bottom-nav">
    <RouterLink :to="{ name: 'frontpage' }" class="tab" active-class="active">
      <svg width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
        <path d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
      </svg>
      <span>{{ t('nav.frontpage') }}</span>
    </RouterLink>

    <RouterLink :to="{ name: 'reader' }" class="tab" active-class="active">
      <svg width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
        <path d="M4 6h16M4 10h16M4 14h16M4 18h16" />
      </svg>
      <span>{{ t('nav.reader') }}</span>
    </RouterLink>

    <!-- Search FAB -->
    <button class="fab" :aria-label="t('search.openSearch')" @click="searchStore.open()">
      <svg width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
        <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
    </button>

    <RouterLink :to="{ name: 'settings' }" class="tab" active-class="active">
      <svg width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
        <path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
      <span>{{ t('nav.settings') }}</span>
    </RouterLink>

    <RouterLink v-if="auth.isAdmin" :to="{ name: 'admin' }" class="tab" active-class="active">
      <svg width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
        <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
      <span>{{ t('nav.admin') }}</span>
    </RouterLink>
    <RouterLink v-else :to="{ name: 'feeds' }" class="tab" active-class="active">
      <svg width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
        <path d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
      </svg>
      <span>{{ t('nav.feeds') }}</span>
    </RouterLink>
  </nav>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useSearchStore } from '@/stores/search'

const { t } = useI18n()
const auth = useAuthStore()
const searchStore = useSearchStore()
</script>

<style scoped>
.bottom-nav {
  display: flex;
  align-items: center;
  justify-content: space-around;
  height: calc(60px + max(env(safe-area-inset-bottom), 0px));
  padding-bottom: max(env(safe-area-inset-bottom), 12px);
  background: var(--bbf-surface);
  border-top: 1px solid var(--bbf-line);
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 30;
}

.tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 6px 12px;
  border-radius: var(--bbf-r-md);
  color: var(--bbf-ink-3);
  text-decoration: none;
  font-size: 10px;
  font-weight: 500;
  transition: color 0.12s;
  flex: 1;
}
.tab:hover { color: var(--bbf-ink-2); }
.tab.active { color: var(--bbf-primary); }

.fab {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--bbf-primary);
  color: #fff;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: var(--bbf-shadow-2);
  transition: background 0.15s, transform 0.12s;
  flex-shrink: 0;
}
.fab:hover { background: var(--bbf-primary-2); }
.fab:active { transform: scale(0.96); }
</style>
