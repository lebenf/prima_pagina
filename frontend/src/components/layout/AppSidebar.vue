<template>
  <aside
    class="flex flex-col bg-primary-900 text-white transition-all duration-200 overflow-hidden shadow-lg"
  >
    <!-- Collapse toggle -->
    <button
      class="p-3 flex justify-end hover:bg-primary-700 transition-colors"
      :title="ui.sidebarCollapsed ? 'Expand' : 'Collapse'"
      @click="ui.toggleCollapse()"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          :d="ui.sidebarCollapsed ? 'M9 5l7 7-7 7' : 'M15 19l-7-7 7-7'"
        />
      </svg>
    </button>

    <AppNavigation :collapsed="ui.sidebarCollapsed" />

    <div class="flex-1" />

    <!-- Bottom: settings + admin -->
    <nav class="pb-4">
      <RouterLink
        :to="{ name: 'settings' }"
        class="flex items-center gap-3 px-4 py-3 hover:bg-primary-700 transition-colors"
        :class="{ 'justify-center': ui.sidebarCollapsed }"
        active-class="bg-primary-600"
      >
        <!-- Gear icon -->
        <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
          />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        <span v-if="!ui.sidebarCollapsed" class="text-sm">{{ t('nav.settings') }}</span>
      </RouterLink>

      <RouterLink
        v-if="auth.isAdmin"
        :to="{ name: 'admin' }"
        class="flex items-center gap-3 px-4 py-3 hover:bg-primary-700 transition-colors"
        :class="{ 'justify-center': ui.sidebarCollapsed }"
        active-class="bg-primary-600"
      >
        <!-- Shield icon -->
        <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
        </svg>
        <span v-if="!ui.sidebarCollapsed" class="text-sm">{{ t('nav.admin') }}</span>
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
