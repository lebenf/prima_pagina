<template>
  <header class="h-14 flex items-center gap-4 px-4 bg-primary-900 text-white shadow-md z-10 flex-shrink-0">
    <!-- Hamburger / logo -->
    <button
      class="p-1.5 rounded hover:bg-primary-700 transition-colors"
      @click="ui.toggleSidebar()"
    >
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
      </svg>
    </button>

    <RouterLink :to="{ name: 'frontpage' }" class="font-serif font-bold text-lg tracking-tight text-newspaper-accent">
      Prima Pagina
    </RouterLink>

    <!-- Search (placeholder) -->
    <div class="flex-1 max-w-md mx-auto hidden md:block">
      <div class="relative">
        <svg class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          type="search"
          :placeholder="t('common.search')"
          class="w-full pl-9 pr-4 py-1.5 text-sm bg-primary-700 rounded-full text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
          disabled
        />
      </div>
    </div>

    <div class="ml-auto flex items-center gap-2">
      <LanguageSwitcher />

      <!-- User dropdown -->
      <div class="relative" ref="userMenuRef">
        <button
          class="flex items-center gap-2 px-3 py-1.5 rounded-full hover:bg-primary-700 transition-colors text-sm"
          @click="userMenuOpen = !userMenuOpen"
        >
          <div class="w-7 h-7 rounded-full bg-primary-500 flex items-center justify-center font-semibold text-xs uppercase">
            {{ auth.user?.username?.charAt(0) ?? '?' }}
          </div>
          <span class="hidden sm:inline">{{ auth.user?.username }}</span>
          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        <Transition name="dropdown">
          <div
            v-if="userMenuOpen"
            class="absolute right-0 top-full mt-1 w-44 bg-white rounded-lg shadow-lg border border-gray-200 py-1 text-gray-700 z-50"
          >
            <RouterLink
              :to="{ name: 'settings' }"
              class="flex items-center gap-2 px-4 py-2 text-sm hover:bg-gray-50"
              @click="userMenuOpen = false"
            >
              {{ t('nav.settings') }}
            </RouterLink>
            <hr class="my-1 border-gray-200" />
            <button
              class="w-full flex items-center gap-2 px-4 py-2 text-sm hover:bg-gray-50 text-red-600"
              @click="handleLogout"
            >
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
import LanguageSwitcher from '@/components/common/LanguageSwitcher.vue'

const { t } = useI18n()
const auth = useAuthStore()
const ui = useUiStore()
const router = useRouter()

const userMenuOpen = ref(false)
const userMenuRef = ref<HTMLElement | null>(null)

onClickOutside(userMenuRef, () => {
  userMenuOpen.value = false
})

async function handleLogout() {
  userMenuOpen.value = false
  await auth.logout()
  await router.push('/login')
}
</script>

<style scoped>
.dropdown-enter-active,
.dropdown-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
