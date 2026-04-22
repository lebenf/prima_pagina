<template>
  <div class="min-h-screen flex items-center justify-center bg-newspaper-bg px-4">
    <div class="w-full max-w-sm">
      <!-- Logo / title -->
      <div class="text-center mb-8">
        <h1 class="font-serif text-3xl font-bold text-primary-900">Prima Pagina</h1>
        <p class="text-sm text-gray-500 mt-1">Il tuo aggregatore RSS personale</p>
      </div>

      <div class="bg-white rounded-xl shadow-sm border border-newspaper-border p-8">
        <form @submit.prevent="handleSubmit" novalidate>
          <div class="space-y-4">
            <div>
              <label for="username" class="block text-sm font-medium text-gray-700 mb-1">
                {{ t('auth.username') }}
              </label>
              <input
                id="username"
                ref="usernameInput"
                v-model="username"
                type="text"
                autocomplete="username"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                :class="{ 'border-red-400': error }"
                :disabled="auth.isLoading"
              />
            </div>

            <div>
              <label for="password" class="block text-sm font-medium text-gray-700 mb-1">
                {{ t('auth.password') }}
              </label>
              <input
                id="password"
                v-model="password"
                type="password"
                autocomplete="current-password"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                :class="{ 'border-red-400': error }"
                :disabled="auth.isLoading"
              />
            </div>

            <!-- Inline error -->
            <p v-if="error" class="text-sm text-red-600" role="alert">
              {{ t('auth.loginError') }}
            </p>

            <button
              type="submit"
              class="w-full py-2.5 bg-primary-600 hover:bg-primary-700 disabled:opacity-60 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
              :disabled="auth.isLoading || !username || !password"
            >
              <span v-if="auth.isLoading">{{ t('auth.loggingIn') }}</span>
              <span v-else>{{ t('auth.login') }}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')
const error = ref(false)
const usernameInput = ref<HTMLInputElement | null>(null)

onMounted(() => {
  usernameInput.value?.focus()
})

async function handleSubmit() {
  if (!username.value || !password.value) return
  error.value = false
  try {
    await auth.login(username.value, password.value)
    const redirect = (route.query.redirect as string) || '/'
    await router.push(redirect)
  } catch {
    error.value = true
    password.value = ''
  }
}
</script>
