<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="login-page">
    <div class="login-wrap">
      <div class="login-brand">
        <h1>Prima Pagina</h1>
        <p>{{ t('auth.tagline', 'Il tuo aggregatore RSS personale') }}</p>
      </div>

      <div class="login-card">
        <form @submit.prevent="handleSubmit" novalidate>
          <div class="field">
            <label for="username">{{ t('auth.username') }}</label>
            <input
              id="username"
              ref="usernameInput"
              v-model="username"
              type="text"
              autocomplete="username"
              required
              :class="{ error: error }"
              :disabled="auth.isLoading"
            />
          </div>

          <div class="field">
            <label for="password">{{ t('auth.password') }}</label>
            <input
              id="password"
              v-model="password"
              type="password"
              autocomplete="current-password"
              required
              :class="{ error: error }"
              :disabled="auth.isLoading"
            />
          </div>

          <p v-if="error" class="field-error" role="alert">{{ t('auth.loginError') }}</p>

          <button type="submit" class="submit-btn" :disabled="auth.isLoading || !username || !password">
            <span v-if="auth.isLoading">{{ t('auth.loggingIn') }}</span>
            <span v-else>{{ t('auth.login') }}</span>
          </button>
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

onMounted(() => usernameInput.value?.focus())

async function handleSubmit() {
  if (!username.value || !password.value) return
  error.value = false
  try {
    await auth.login(username.value, password.value)
    await router.push((route.query.redirect as string) || '/')
  } catch {
    error.value = true
    password.value = ''
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bbf-bg);
  padding: var(--bbf-s-4);
}

.login-wrap {
  width: 100%;
  max-width: 360px;
}

.login-brand {
  text-align: center;
  margin-bottom: var(--bbf-s-7);
}
.login-brand h1 {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.6px;
  color: var(--bbf-ink);
  margin: 0 0 var(--bbf-s-1);
}
.login-brand p {
  font-size: 13px;
  color: var(--bbf-ink-3);
  margin: 0;
}

.login-card {
  background: var(--bbf-surface);
  border: 1px solid var(--bbf-line);
  border-radius: var(--bbf-r-xl);
  padding: var(--bbf-s-7) var(--bbf-s-6);
  box-shadow: var(--bbf-shadow-2);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-bottom: var(--bbf-s-4);
}
.field label {
  font-size: 12px;
  font-weight: 600;
  color: var(--bbf-ink-2);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.field input {
  padding: 9px 12px;
  background: var(--bbf-surface-2);
  border: 1px solid var(--bbf-line-strong);
  border-radius: var(--bbf-r-md);
  font-size: 14px;
  color: var(--bbf-ink);
  font-family: var(--bbf-font);
  transition: border-color 0.15s;
}
.field input:focus { border-color: var(--bbf-primary); outline: none; }
.field input.error { border-color: var(--bbf-danger); }
.field input:disabled { opacity: 0.55; cursor: not-allowed; }

.field-error {
  font-size: 13px;
  color: var(--bbf-danger);
  background: var(--bbf-danger-soft);
  padding: 8px 12px;
  border-radius: var(--bbf-r-sm);
  margin-bottom: var(--bbf-s-3);
}

.submit-btn {
  width: 100%;
  padding: 10px;
  background: var(--bbf-primary);
  color: white;
  border: none;
  border-radius: var(--bbf-r-md);
  font-size: 14px;
  font-weight: 600;
  font-family: var(--bbf-font);
  cursor: pointer;
  transition: background 0.15s, opacity 0.15s;
}
.submit-btn:hover:not(:disabled) { background: var(--bbf-primary-2); }
.submit-btn:disabled { opacity: 0.55; cursor: not-allowed; }
</style>
