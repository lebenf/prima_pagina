<template>
  <div class="flex flex-col h-screen bg-newspaper-bg text-newspaper-text overflow-hidden">
    <AppHeader />

    <div class="flex flex-1 overflow-hidden relative">
      <!-- Mobile overlay -->
      <Transition name="fade">
        <div
          v-if="ui.sidebarOpen && isMobile"
          class="fixed inset-0 bg-black/40 z-20"
          @click="ui.toggleSidebar()"
        />
      </Transition>

      <!-- Sidebar -->
      <Transition name="slide">
        <AppSidebar
          v-if="ui.sidebarOpen"
          :class="[
            isMobile ? 'fixed left-0 top-0 h-full z-30 mt-14' : 'relative',
            ui.sidebarCollapsed ? 'w-16' : 'w-56',
          ]"
        />
      </Transition>

      <!-- Main content -->
      <main class="flex-1 overflow-y-auto">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { RouterView } from 'vue-router'
import { useWindowSize } from '@vueuse/core'
import { useUiStore } from '@/stores/ui'
import AppHeader from './AppHeader.vue'
import AppSidebar from './AppSidebar.vue'

const ui = useUiStore()
const { width } = useWindowSize()
const isMobile = computed(() => width.value < 768)
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: transform 0.25s ease, width 0.25s ease;
}
.slide-enter-from,
.slide-leave-to {
  transform: translateX(-100%);
}
</style>
