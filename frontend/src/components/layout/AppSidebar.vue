<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <aside class="sidebar" :class="{ collapsed: ui.sidebarCollapsed }">
    <!-- Collapse toggle (desktop only) -->
    <div class="sidebar-top">
      <button class="collapse-btn" :title="ui.sidebarCollapsed ? t('nav.expand') : t('nav.collapse')" @click="ui.toggleCollapse()">
        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
          <path :d="ui.sidebarCollapsed ? 'M9 5l7 7-7 7' : 'M15 19l-7-7 7-7'" />
        </svg>
      </button>
    </div>

    <AppNavigation :collapsed="ui.sidebarCollapsed" />

    <div class="sidebar-spacer" />

    <!-- Bottom nav: settings + feeds/admin -->
    <nav class="sidebar-bottom">
      <RouterLink
        :to="{ name: 'settings' }"
        class="nav-item"
        :class="{ collapsed: ui.sidebarCollapsed }"
        active-class="active"
      >
        <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
          <path d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        <span v-if="!ui.sidebarCollapsed" class="nav-label">{{ t('nav.settings') }}</span>
      </RouterLink>

      <RouterLink
        v-if="!auth.isAdmin"
        :to="{ name: 'feeds' }"
        class="nav-item"
        :class="{ collapsed: ui.sidebarCollapsed }"
        active-class="active"
      >
        <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
          <path d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
        </svg>
        <span v-if="!ui.sidebarCollapsed" class="nav-label">{{ t('nav.feeds') }}</span>
      </RouterLink>

      <RouterLink
        v-if="auth.isAdmin"
        :to="{ name: 'admin' }"
        class="nav-item"
        :class="{ collapsed: ui.sidebarCollapsed }"
        active-class="active"
      >
        <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
          <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
        <span v-if="!ui.sidebarCollapsed" class="nav-label">{{ t('nav.admin') }}</span>
      </RouterLink>
    </nav>
  </aside>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import AppNavigation from './AppNavigation.vue'

const { t } = useI18n()
const ui = useUiStore()
const auth = useAuthStore()
</script>

<style scoped>
.sidebar {
  width: 240px;
  min-width: 240px;
  display: flex;
  flex-direction: column;
  background: var(--bbf-surface);
  border-right: 1px solid var(--bbf-line);
  overflow: hidden;
  transition: width 0.2s ease, min-width 0.2s ease;
}
.sidebar.collapsed {
  width: 64px;
  min-width: 64px;
}

.sidebar-top {
  display: flex;
  justify-content: flex-end;
  padding: var(--bbf-s-3) var(--bbf-s-3) var(--bbf-s-2);
}

.collapse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: none;
  border-radius: var(--bbf-r-sm);
  color: var(--bbf-ink-3);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.collapse-btn:hover { background: var(--bbf-surface-2); color: var(--bbf-ink); }

.sidebar-spacer { flex: 1; }

.sidebar-bottom {
  padding: var(--bbf-s-2) var(--bbf-s-2) var(--bbf-s-3);
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
