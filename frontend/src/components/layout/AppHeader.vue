<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <header class="app-topbar">
    <!-- Hamburger -->
    <button class="icon-btn" :aria-label="t('nav.toggleMenu')" @click="ui.toggleSidebar()">
      <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
        <path d="M4 6h16M4 12h16M4 18h16" />
      </svg>
    </button>

    <RouterLink :to="{ name: 'frontpage' }" class="brand">Prima Pagina</RouterLink>

    <!-- Search trigger -->
    <div class="search-wrap">
      <button class="search-btn" :aria-label="t('search.openSearch')" @click="searchStore.open()">
        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
          <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <span>{{ t('search.search') }}</span>
        <kbd>Ctrl K</kbd>
      </button>
    </div>

    <div class="actions">
      <LanguageSwitcher />

      <!-- Dark mode toggle -->
      <button class="icon-btn" :aria-label="t('settings.toggleTheme')" @click="toggleTheme()">
        <svg v-if="theme === 'dark'" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
          <path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m12.728 0l-.707-.707M6.343 6.343l-.707-.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
        </svg>
        <svg v-else width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
          <path d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
        </svg>
      </button>

      <!-- User menu -->
      <div class="user-menu-wrap" ref="userMenuRef">
        <button class="user-btn" @click="userMenuOpen = !userMenuOpen">
          <div class="avatar">{{ auth.user?.username?.charAt(0)?.toUpperCase() ?? '?' }}</div>
          <span class="username">{{ auth.user?.username }}</span>
          <svg width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        <Transition name="dropdown">
          <div v-if="userMenuOpen" class="dropdown">
            <RouterLink :to="{ name: 'settings' }" class="dropdown-item" @click="userMenuOpen = false">
              {{ t('nav.settings') }}
            </RouterLink>
            <div class="dropdown-divider" />
            <button class="dropdown-item danger" @click="handleLogout">
              {{ t('nav.logout') }}
            </button>
          </div>
        </Transition>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { onClickOutside } from '@vueuse/core'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { useSearchStore } from '@/stores/search'
import { useTheme } from '@/composables/useTheme'
import LanguageSwitcher from '@/components/common/LanguageSwitcher.vue'

const { t } = useI18n()
const auth = useAuthStore()
const ui = useUiStore()
const router = useRouter()
const searchStore = useSearchStore()
const { theme, toggle: toggleTheme } = useTheme()

const userMenuOpen = ref(false)
const userMenuRef = ref<HTMLElement | null>(null)

onClickOutside(userMenuRef, () => { userMenuOpen.value = false })

async function handleLogout() {
  userMenuOpen.value = false
  await auth.logout()
  await router.push('/login')
}
</script>

<style scoped>
.app-topbar {
  height: 56px;
  display: flex;
  align-items: center;
  gap: var(--bbf-s-3);
  padding: max(env(safe-area-inset-top), 0px) var(--bbf-s-4) 0;
  padding-top: calc(max(env(safe-area-inset-top), 0px) + 0px);
  height: calc(56px + max(env(safe-area-inset-top), 0px));
  background: var(--bbf-surface);
  border-bottom: 1px solid var(--bbf-line);
  position: sticky;
  top: 0;
  z-index: 40;
  flex-shrink: 0;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  background: none;
  border-radius: var(--bbf-r-md);
  color: var(--bbf-ink-2);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  flex-shrink: 0;
}
.icon-btn:hover { background: var(--bbf-surface-2); color: var(--bbf-ink); }

.brand {
  font-weight: 700;
  font-size: 17px;
  letter-spacing: -0.4px;
  color: var(--bbf-primary-ink);
  text-decoration: none;
  flex-shrink: 0;
}
.brand:hover { color: var(--bbf-primary); }

.search-wrap {
  flex: 1;
  max-width: 360px;
  margin: 0 auto;
  display: none;
}
@media (min-width: 768px) { .search-wrap { display: block; } }

.search-btn {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--bbf-s-2);
  padding: 0 var(--bbf-s-3);
  height: 34px;
  background: var(--bbf-surface-2);
  border: 1px solid var(--bbf-line);
  border-radius: var(--bbf-r-xl);
  color: var(--bbf-ink-3);
  font-family: var(--bbf-font);
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.search-btn:hover { background: var(--bbf-surface-3); border-color: var(--bbf-line-strong); }
.search-btn span { flex: 1; text-align: left; }
.search-btn kbd {
  font-family: var(--bbf-mono);
  font-size: 11px;
  padding: 1px 5px;
  background: var(--bbf-surface-3);
  border: 1px solid var(--bbf-line-strong);
  border-radius: var(--bbf-r-xs);
  color: var(--bbf-ink-3);
}

.actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: var(--bbf-s-1);
}

.user-menu-wrap { position: relative; }

.user-btn {
  display: flex;
  align-items: center;
  gap: var(--bbf-s-2);
  padding: 4px 10px 4px 4px;
  background: none;
  border: 1px solid transparent;
  border-radius: var(--bbf-r-xl);
  cursor: pointer;
  color: var(--bbf-ink);
  transition: background 0.15s, border-color 0.15s;
  font-family: var(--bbf-font);
  font-size: 13px;
  font-weight: 500;
}
.user-btn:hover { background: var(--bbf-surface-2); border-color: var(--bbf-line); }

.avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--bbf-primary-soft);
  color: var(--bbf-primary-ink);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.username { display: none; }
@media (min-width: 640px) { .username { display: inline; } }

.dropdown {
  position: absolute;
  right: 0;
  top: calc(100% + 6px);
  width: 176px;
  background: var(--bbf-surface);
  border: 1px solid var(--bbf-line);
  border-radius: var(--bbf-r-lg);
  box-shadow: var(--bbf-shadow-3);
  padding: 4px;
  z-index: 50;
}

.dropdown-item {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 500;
  color: var(--bbf-ink-2);
  background: none;
  border: none;
  border-radius: var(--bbf-r-sm);
  text-decoration: none;
  cursor: pointer;
  transition: background 0.12s, color 0.12s;
  font-family: var(--bbf-font);
  text-align: left;
}
.dropdown-item:hover { background: var(--bbf-surface-2); color: var(--bbf-ink); }
.dropdown-item.danger { color: var(--bbf-danger); }
.dropdown-item.danger:hover { background: var(--bbf-danger-soft); }

.dropdown-divider {
  height: 1px;
  background: var(--bbf-line);
  margin: 4px 0;
}

/* Dropdown animation */
.dropdown-enter-active, .dropdown-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.dropdown-enter-from, .dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
