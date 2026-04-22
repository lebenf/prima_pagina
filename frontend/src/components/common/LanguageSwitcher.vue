<template>
  <div class="relative" ref="containerRef">
    <button
      class="flex items-center gap-1.5 px-2.5 py-1.5 rounded hover:bg-primary-700 transition-colors text-sm font-medium"
      @click="open = !open"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
      </svg>
      <span class="uppercase">{{ currentLocale }}</span>
    </button>

    <Transition name="dropdown">
      <div
        v-if="open"
        class="absolute right-0 top-full mt-1 w-36 bg-white rounded-lg shadow-lg border border-gray-200 py-1 text-gray-700 z-50"
      >
        <button
          v-for="loc in SUPPORTED_LOCALES"
          :key="loc"
          class="w-full text-left px-4 py-2 text-sm hover:bg-gray-50 flex items-center justify-between"
          :class="{ 'font-semibold text-primary-600': loc === currentLocale }"
          @click="selectLocale(loc)"
        >
          {{ t(`languages.${loc}`) }}
          <svg v-if="loc === currentLocale" class="w-3.5 h-3.5 text-primary-500" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
          </svg>
        </button>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { onClickOutside } from '@vueuse/core'
import { setLocale, SUPPORTED_LOCALES } from '@/i18n'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth'

const { t, locale } = useI18n()
const auth = useAuthStore()

const open = ref(false)
const containerRef = ref<HTMLElement | null>(null)
const currentLocale = computed(() => locale.value)

onClickOutside(containerRef, () => {
  open.value = false
})

async function selectLocale(loc: string) {
  open.value = false
  await setLocale(loc)
  if (auth.isAuthenticated) {
    await authApi.updateMe({ preferred_lang: loc })
    if (auth.user) {
      auth.user.preferred_lang = loc
    }
  }
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
