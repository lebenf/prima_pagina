<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="admin-section">
    <div class="section-header">
      <h2>{{ t('admin.users.title') }}</h2>
      <button class="btn-primary" @click="openCreate">+ {{ t('admin.users.newUser') }}</button>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>
    <div v-else>
      <table class="admin-table">
        <thead>
          <tr>
            <th>Username</th>
            <th>Email</th>
            <th>{{ t('admin.users.role') }}</th>
            <th>Lingua</th>
            <th>{{ t('admin.users.active') }}</th>
            <th>Azioni</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id" :class="{ 'row-inactive': !user.is_active }">
            <td>
              {{ user.username }}
              <span v-if="user.id === currentUser?.id" class="badge badge-self">tu</span>
            </td>
            <td>{{ user.email }}</td>
            <td>
              <span :class="['badge', user.role === 'admin' ? 'badge-admin' : 'badge-user']">
                {{ user.role }}
              </span>
            </td>
            <td>{{ user.preferred_lang.toUpperCase() }}</td>
            <td>{{ user.is_active ? '✓' : '✗' }}</td>
            <td class="actions">
              <button class="btn-icon" @click="openEdit(user)" title="Modifica">✏️</button>
              <button
                class="btn-icon"
                :disabled="user.id === currentUser?.id"
                :title="user.id === currentUser?.id ? t('admin.users.cannotDeleteSelf') : t('common.delete')"
                @click="confirmDelete(user)"
              >🗑️</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <UserFormModal
      v-if="showModal"
      :user="editingUser"
      :is-self="editingUser?.id === currentUser?.id"
      @close="showModal = false"
      @saved="onSaved"
    />

    <ConfirmDialog
      v-if="showConfirm"
      :title="t('common.delete')"
      :message="t('admin.users.deleteConfirm', { username: deletingUser?.username })"
      @confirm="doDelete"
      @cancel="showConfirm = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { adminApi, type AdminUser } from '@/api/admin'
import UserFormModal from './UserFormModal.vue'
import ConfirmDialog from './ConfirmDialog.vue'

const { t } = useI18n()
const auth = useAuthStore()
const currentUser = auth.user

const users = ref<AdminUser[]>([])
const loading = ref(false)
const error = ref('')
const showModal = ref(false)
const editingUser = ref<AdminUser | null>(null)
const showConfirm = ref(false)
const deletingUser = ref<AdminUser | null>(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await adminApi.users.list()
    users.value = res.data
  } catch {
    error.value = t('common.error')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingUser.value = null
  showModal.value = true
}

function openEdit(user: AdminUser) {
  editingUser.value = user
  showModal.value = true
}

function confirmDelete(user: AdminUser) {
  if (user.id === currentUser?.id) return
  deletingUser.value = user
  showConfirm.value = true
}

async function doDelete() {
  if (!deletingUser.value) return
  try {
    await adminApi.users.delete(deletingUser.value.id)
    users.value = users.value.filter(u => u.id !== deletingUser.value!.id)
  } catch {
    error.value = t('common.error')
  } finally {
    showConfirm.value = false
    deletingUser.value = null
  }
}

function onSaved(user: AdminUser) {
  const idx = users.value.findIndex(u => u.id === user.id)
  if (idx >= 0) {
    users.value[idx] = user
  } else {
    users.value.push(user)
  }
  showModal.value = false
}

onMounted(load)
</script>

<style scoped>
.admin-section {
  padding: 1.5rem;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.25rem;
}

.section-header h2 {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0;
}

.admin-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.admin-table th {
  text-align: left;
  padding: 0.75rem 1rem;
  border-bottom: 2px solid #e5e5e5;
  font-weight: 600;
  color: #555;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.admin-table td {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #f0f0f0;
  vertical-align: middle;
}

.row-inactive td {
  color: #aaa;
}

.badge {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.badge-admin {
  background: #fef3c7;
  color: #92400e;
}

.badge-user {
  background: #e0e7ff;
  color: #3730a3;
}

.badge-self {
  background: #d1fae5;
  color: #065f46;
  margin-left: 0.5rem;
}

.actions {
  display: flex;
  gap: 0.25rem;
}

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  padding: 0.25rem;
  border-radius: 4px;
  opacity: 0.7;
  transition: opacity 0.15s;
}

.btn-icon:hover:not(:disabled) {
  opacity: 1;
  background: #f0f0f0;
}

.btn-icon:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.btn-primary {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  background: #1a1a1a;
  color: white;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 600;
}

.loading, .error-msg {
  padding: 2rem;
  text-align: center;
  color: #888;
}

.error-msg {
  color: #dc2626;
}
</style>
