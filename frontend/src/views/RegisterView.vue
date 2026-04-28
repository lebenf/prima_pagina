<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="register-page">
    <div class="register-card">
      <div class="register-logo">Prima Pagina</div>

      <div v-if="validating" class="register-loading">
        <span class="spinner">⏳</span>
        {{ t('auth.validatingInvite') }}
      </div>

      <div v-else-if="!inviteValid" class="register-error">
        <h2>{{ t('auth.inviteInvalid') }}</h2>
        <p>{{ t('auth.inviteInvalidDesc') }}</p>
        <RouterLink to="/login" class="back-link">← {{ t('auth.login') }}</RouterLink>
      </div>

      <template v-else>
        <h1 class="register-title">{{ t('auth.createAccount') }}</h1>
        <p class="register-subtitle">{{ t('auth.invitedBy') }}</p>

        <form @submit.prevent="handleRegister" class="register-form">
          <div class="form-group">
            <label>{{ t('auth.username') }}</label>
            <input v-model="form.username" type="text" required minlength="3" autocomplete="username" />
          </div>

          <div class="form-group">
            <label>Email</label>
            <input
              v-model="form.email"
              type="email"
              required
              :readonly="!!prefillEmail"
              autocomplete="email"
            />
          </div>

          <div class="form-group">
            <label>{{ t('auth.password') }}</label>
            <input v-model="form.password" type="password" required minlength="8" autocomplete="new-password" />
          </div>

          <div class="form-group">
            <label>{{ t('auth.confirmPassword') }}</label>
            <input v-model="form.confirm_password" type="password" required autocomplete="new-password" />
            <span v-if="passwordMismatch" class="field-error">
              {{ t('auth.passwordMismatch') }}
            </span>
          </div>

          <div v-if="error" class="form-error">{{ error }}</div>

          <button type="submit" :disabled="isLoading || passwordMismatch" class="submit-btn">
            {{ isLoading ? t('auth.registering') : t('auth.register') }}
          </button>
        </form>

        <div class="register-footer">
          <RouterLink to="/login" class="back-link">← {{ t('auth.login') }}</RouterLink>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useI18n } from 'vue-i18n'
import client from '@/api/client'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { t } = useI18n()

const token = route.query.token as string | undefined
const validating = ref(true)
const inviteValid = ref(false)
const prefillEmail = ref<string | null>(null)
const isLoading = ref(false)
const error = ref<string | null>(null)

const form = ref({
  username: '',
  email: '',
  password: '',
  confirm_password: '',
})

const passwordMismatch = computed(() =>
  form.value.confirm_password.length > 0 &&
  form.value.password !== form.value.confirm_password
)

onMounted(async () => {
  if (auth.isAuthenticated) {
    await router.replace('/')
    return
  }

  if (!token) {
    inviteValid.value = false
    validating.value = false
    return
  }

  try {
    const res = await client.get(`/auth/invitation/${token}`)
    inviteValid.value = res.data.valid
    if (res.data.email) {
      prefillEmail.value = res.data.email
      form.value.email = res.data.email
    }
  } catch {
    inviteValid.value = false
  } finally {
    validating.value = false
  }
})

async function handleRegister() {
  if (passwordMismatch.value) return
  isLoading.value = true
  error.value = null
  try {
    await client.post(`/auth/register/${token}`, form.value)
    await auth.fetchMe()
    await router.push('/')
  } catch (e: any) {
    error.value = e.response?.data?.detail || t('auth.registerError')
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f9fafb;
  padding: 1rem;
}

.register-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.1);
  padding: 2.5rem;
  width: 100%;
  max-width: 420px;
}

.register-logo {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 1.5rem;
  font-weight: 700;
  text-align: center;
  margin-bottom: 1.5rem;
  color: #111827;
}

.register-title {
  font-size: 1.25rem;
  font-weight: 700;
  text-align: center;
  margin: 0 0 0.25rem;
  color: #111827;
}

.register-subtitle {
  text-align: center;
  font-size: 0.875rem;
  color: #6b7280;
  margin-bottom: 1.5rem;
}

.register-loading {
  text-align: center;
  color: #6b7280;
  padding: 2rem 0;
}

.register-error {
  text-align: center;
}

.register-error h2 {
  font-size: 1.1rem;
  font-weight: 700;
  color: #dc2626;
  margin-bottom: 0.5rem;
}

.register-error p {
  font-size: 0.875rem;
  color: #6b7280;
  margin-bottom: 1rem;
}

.register-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.form-group label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
}

.form-group input {
  padding: 0.625rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 0.875rem;
  transition: border-color 0.15s;
}

.form-group input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.form-group input[readonly] {
  background: #f3f4f6;
  color: #6b7280;
}

.field-error {
  font-size: 0.8rem;
  color: #dc2626;
}

.form-error {
  font-size: 0.875rem;
  color: #dc2626;
  background: #fef2f2;
  border-radius: 4px;
  padding: 0.5rem 0.75rem;
}

.submit-btn {
  padding: 0.75rem;
  background: #111827;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
  margin-top: 0.5rem;
}

.submit-btn:hover:not(:disabled) {
  background: #374151;
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.register-footer {
  text-align: center;
  margin-top: 1.25rem;
  font-size: 0.875rem;
}

.back-link {
  color: #2563eb;
  text-decoration: none;
}

.back-link:hover {
  text-decoration: underline;
}
</style>
