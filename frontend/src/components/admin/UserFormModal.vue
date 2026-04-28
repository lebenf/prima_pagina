<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <Teleport to="body">
    <div class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-dialog" role="dialog" aria-modal="true">
        <div class="modal-header">
          <h3>{{ isEdit ? t('admin.users.editUser') : t('admin.users.newUser') }}</h3>
          <button class="close-btn" @click="$emit('close')">×</button>
        </div>

        <form @submit.prevent="submit" class="modal-form">
          <div class="form-group">
            <label>{{ t('auth.username') }}</label>
            <input v-model="form.username" type="text" required :placeholder="t('auth.username')" />
          </div>

          <div class="form-group">
            <label>Email</label>
            <input v-model="form.email" type="email" required placeholder="email@example.com" />
          </div>

          <div class="form-group">
            <label>{{ t('auth.password') }}{{ isEdit ? ' (lascia vuoto per non cambiare)' : '' }}</label>
            <input v-model="form.password" type="password" :required="!isEdit" placeholder="••••••••" />
          </div>

          <div v-if="!isEdit" class="form-group">
            <label>{{ t('admin.users.confirmPassword') }}</label>
            <input
              v-model="form.confirm_password"
              type="password"
              required
              placeholder="••••••••"
            />
            <span v-if="passwordMismatch" class="field-error">{{ t('auth.passwordMismatch') }}</span>
          </div>

          <div class="form-group">
            <label>{{ t('admin.users.role') }}</label>
            <select v-model="form.role" :disabled="isSelf">
              <option value="user">user</option>
              <option value="admin">admin</option>
            </select>
            <small v-if="isSelf" class="hint">Non puoi cambiare il tuo ruolo</small>
          </div>

          <div class="form-group">
            <label>Lingua preferita</label>
            <select v-model="form.preferred_lang">
              <option v-for="lang in langs" :key="lang.code" :value="lang.code">{{ lang.label }}</option>
            </select>
          </div>

          <div v-if="isEdit" class="form-group form-group-inline">
            <label>{{ t('admin.users.active') }}</label>
            <input v-model="form.is_active" type="checkbox" />
          </div>

          <div v-if="error" class="form-error">{{ error }}</div>

          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="$emit('close')">{{ t('common.cancel') }}</button>
            <button type="submit" class="btn-primary" :disabled="saving || passwordMismatch">
              {{ saving ? t('common.loading') : t('common.save') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { adminApi, type AdminUser, type UserCreate, type UserUpdate } from '@/api/admin'

const props = defineProps<{
  user?: AdminUser | null
  isSelf?: boolean
}>()

const emit = defineEmits<{
  close: []
  saved: [user: AdminUser]
}>()

const { t } = useI18n()
const isEdit = computed(() => !!props.user)

const langs = [
  { code: 'it', label: 'Italiano' },
  { code: 'en', label: 'English' },
  { code: 'fr', label: 'Français' },
  { code: 'de', label: 'Deutsch' },
  { code: 'es', label: 'Español' },
  { code: 'pt', label: 'Português' },
]

const defaultForm = () => ({
  username: '',
  email: '',
  password: '',
  confirm_password: '',
  role: 'user' as 'admin' | 'user',
  preferred_lang: 'it',
  is_active: true,
})

const passwordMismatch = computed(() =>
  !isEdit.value &&
  form.value.confirm_password.length > 0 &&
  form.value.password !== form.value.confirm_password
)

const form = ref(defaultForm())
const saving = ref(false)
const error = ref('')

watch(() => props.user, (u) => {
  if (u) {
    form.value = {
      username: u.username,
      email: u.email,
      password: '',
      role: u.role,
      preferred_lang: u.preferred_lang,
      is_active: u.is_active,
    }
  } else {
    form.value = defaultForm()
  }
}, { immediate: true })

async function submit() {
  error.value = ''
  saving.value = true
  try {
    if (isEdit.value && props.user) {
      const payload: UserUpdate = {
        email: form.value.email,
        username: form.value.username,
        preferred_lang: form.value.preferred_lang,
        is_active: form.value.is_active,
      }
      if (!props.isSelf) payload.role = form.value.role
      if (form.value.password) payload.password = form.value.password
      const res = await adminApi.users.update(props.user.id, payload)
      emit('saved', res.data)
    } else {
      const payload: UserCreate = {
        username: form.value.username,
        email: form.value.email,
        password: form.value.password,
        confirm_password: form.value.confirm_password,
        role: form.value.role,
        preferred_lang: form.value.preferred_lang,
      }
      const res = await adminApi.users.create(payload)
      emit('saved', res.data)
    }
  } catch (e: any) {
    error.value = e.response?.data?.detail || t('common.error')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 900;
}

.modal-dialog {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 480px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid #e5e5e5;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 700;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #666;
  line-height: 1;
}

.modal-form {
  padding: 1.5rem;
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
  color: #444;
}

.form-group input[type="text"],
.form-group input[type="email"],
.form-group input[type="password"],
.form-group select {
  padding: 0.5rem 0.75rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.875rem;
}

.form-group-inline {
  flex-direction: row;
  align-items: center;
  gap: 0.5rem;
}

.hint {
  font-size: 0.75rem;
  color: #888;
}

.field-error {
  font-size: 0.8rem;
  color: #dc2626;
}

.form-error {
  color: #dc2626;
  font-size: 0.875rem;
  padding: 0.5rem;
  background: #fef2f2;
  border-radius: 4px;
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
  margin-top: 0.5rem;
}

.btn-primary {
  padding: 0.5rem 1.25rem;
  border: none;
  border-radius: 4px;
  background: #1a1a1a;
  color: white;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 600;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 0.5rem 1.25rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  font-size: 0.875rem;
}
</style>
