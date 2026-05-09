<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="app-shell">
    <AppHeader />

    <div class="shell-body">
      <!-- Mobile overlay -->
      <Transition name="fade">
        <div
          v-if="ui.sidebarOpen && isMobile"
          class="overlay"
          @click="ui.toggleSidebar()"
        />
      </Transition>

      <!-- Sidebar: visible on tablet+ always; on mobile as overlay -->
      <Transition name="slide">
        <AppSidebar
          v-if="ui.sidebarOpen || !isMobile"
          :class="isMobile ? 'sidebar-overlay' : 'sidebar-static'"
          :style="{ width: sidebarWidth }"
        />
      </Transition>

      <!-- Main content -->
      <main class="main-content" :class="{ 'has-bottom-nav': isMobile }">
        <RouterView />
      </main>
    </div>

    <!-- Bottom nav on mobile -->
    <BottomNav v-if="isMobile" />
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import { RouterView } from 'vue-router'
import { useWindowSize } from '@vueuse/core'
import { useUiStore } from '@/stores/ui'
import AppHeader from './AppHeader.vue'
import AppSidebar from './AppSidebar.vue'
import BottomNav from './BottomNav.vue'

const ui = useUiStore()
const { width } = useWindowSize()

const isMobile = computed(() => width.value < 1024)
const isTablet = computed(() => width.value >= 768 && width.value < 1024)

const sidebarWidth = computed(() => {
  if (isTablet.value || ui.sidebarCollapsed) return '64px'
  return '240px'
})

// On tablet: auto-collapse sidebar to icons
watch(isTablet, (tablet) => {
  if (tablet) ui.sidebarCollapsed = true
  else if (width.value >= 1024) ui.sidebarCollapsed = false
}, { immediate: true })

// On mobile: close sidebar when resizing up
watch(isMobile, (mobile) => {
  if (!mobile) ui.sidebarOpen = true
  else ui.sidebarOpen = false
}, { immediate: true })
</script>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100dvh;
  background: var(--bbf-bg);
  overflow: hidden;
}

.shell-body {
  display: flex;
  flex: 1;
  overflow: hidden;
  position: relative;
}

.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 20;
}

.sidebar-static {
  position: relative;
  flex-shrink: 0;
  transition: width 0.2s ease;
}

.sidebar-overlay {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  z-index: 30;
  margin-top: 56px;
}

.main-content {
  flex: 1;
  overflow-y: auto;
  min-width: 0;
}
.main-content.has-bottom-nav {
  padding-bottom: calc(72px + max(env(safe-area-inset-bottom), 0px));
}

/* Sidebar transitions */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.slide-enter-active, .slide-leave-active { transition: transform 0.25s ease; }
.slide-enter-from, .slide-leave-to { transform: translateX(-100%); }
</style>
