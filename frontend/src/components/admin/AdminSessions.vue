<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="admin-section">
    <div class="section-header">
      <h2>{{ t('admin.sessions.title') }}</h2>
      <button class="btn-secondary" @click="load">{{ t('admin.sessions.refresh') }}</button>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>
    <div v-else-if="sessions.length === 0" class="empty">{{ t('admin.sessions.noSessions') }}</div>
    <div v-else>
      <div class="filter-bar">
        <label>Filtro utente:</label>
        <select v-model="filterUser">
          <option value="">Tutti gli utenti</option>
          <option v-for="u in uniqueUsers" :key="u.id" :value="u.id">{{ u.username }}</option>
        </select>
      </div>

      <table class="admin-table">
        <thead>
          <tr>
            <th>Utente</th>
            <th>IP</th>
            <th>{{ t('admin.sessions.lastActive') }}</th>
            <th>{{ t('admin.sessions.expiresAt') }}</th>
            <th>Stato</th>
            <th>Azioni</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="session in filteredSessions"
            :key="session.id"
            :class="{ 'row-current': isCurrentSession(session), 'row-revoked': session.is_revoked }"
          >
            <td>
              {{ session.username }}
              <span v-if="isCurrentSession(session)" class="badge badge-current">
                {{ t('admin.sessions.currentSession') }}
              </span>
            </td>
            <td>{{ session.ip_address || '—' }}</td>
            <td>{{ formatDate(session.last_active_at) }}</td>
            <td>{{ formatDate(session.expires_at) }}</td>
            <td>
              <span :class="['badge', sessionBadgeClass(session)]">
                {{ sessionStatusLabel(session) }}
              </span>
            </td>
            <td class="actions">
              <button
                class="btn-sm btn-danger"
                :disabled="isCurrentSession(session) || session.is_revoked"
                @click="confirmRevoke(session)"
              >
                Revoca
              </button>
              <button
                v-if="!isCurrentSession(session)"
                class="btn-sm"
                @click="revokeAllForUser(session.user_id)"
                :title="t('admin.sessions.revokeAll')"
              >
                {{ t('admin.sessions.revokeAll') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <ConfirmDialog
      v-if="showConfirm"
      :title="'Revoca sessione'"
      :message="t('admin.sessions.revokeConfirm', { username: revokingSession?.username })"
      @confirm="doRevoke"
      @cancel="showConfirm = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { adminApi, type AdminSession } from '@/api/admin'
import ConfirmDialog from './ConfirmDialog.vue'

const { t } = useI18n()
const auth = useAuthStore()

const sessions = ref<AdminSession[]>([])
const loading = ref(false)
const error = ref('')
const filterUser = ref('')
const showConfirm = ref(false)
const revokingSession = ref<AdminSession | null>(null)

const currentSessionId = computed(() => {
  const cookie = document.cookie.match(/pp_session=([^;]+)/)
  return cookie ? cookie[1] : null
})

const uniqueUsers = computed(() => {
  const seen = new Set<string>()
  return sessions.value
    .filter(s => { if (seen.has(s.user_id)) return false; seen.add(s.user_id); return true })
    .map(s => ({ id: s.user_id, username: s.username }))
})

const filteredSessions = computed(() =>
  filterUser.value
    ? sessions.value.filter(s => s.user_id === filterUser.value)
    : sessions.value
)

function isCurrentSession(s: AdminSession) {
  return s.id === currentSessionId.value || s.user_id === auth.user?.id && !s.is_revoked
}

function sessionBadgeClass(s: AdminSession) {
  if (s.is_revoked) return 'badge-revoked'
  const daysLeft = (new Date(s.expires_at).getTime() - Date.now()) / 86400000
  if (daysLeft < 7) return 'badge-warn'
  return 'badge-active'
}

function sessionStatusLabel(s: AdminSession) {
  if (s.is_revoked) return 'Revocata'
  const daysLeft = (new Date(s.expires_at).getTime() - Date.now()) / 86400000
  if (daysLeft < 0) return 'Scaduta'
  if (daysLeft < 7) return 'Scade presto'
  return 'Attiva'
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString()
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await adminApi.sessions.list()
    sessions.value = res.data
  } catch {
    error.value = t('common.error')
  } finally {
    loading.value = false
  }
}

function confirmRevoke(session: AdminSession) {
  revokingSession.value = session
  showConfirm.value = true
}

async function doRevoke() {
  if (!revokingSession.value) return
  try {
    await adminApi.sessions.revoke(revokingSession.value.id)
    const idx = sessions.value.findIndex(s => s.id === revokingSession.value!.id)
    if (idx >= 0) sessions.value[idx].is_revoked = true
  } catch {
    error.value = t('common.error')
  } finally {
    showConfirm.value = false
    revokingSession.value = null
  }
}

async function revokeAllForUser(userId: string) {
  try {
    await adminApi.sessions.revokeAllForUser(userId)
    sessions.value = sessions.value.map(s =>
      s.user_id === userId && !isCurrentSession(s) ? { ...s, is_revoked: true } : s
    )
  } catch {
    error.value = t('common.error')
  }
}

onMounted(load)
</script>

<style scoped>
.admin-section { padding: 1.5rem; }
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.25rem;
}
.section-header h2 { font-size: 1.25rem; font-weight: 700; margin: 0; }
.filter-bar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
  font-size: 0.875rem;
}
.filter-bar select { padding: 0.25rem 0.5rem; border: 1px solid #ccc; border-radius: 4px; }
.admin-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
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
.admin-table td { padding: 0.75rem 1rem; border-bottom: 1px solid #f0f0f0; vertical-align: middle; }
.row-current { background: #f0fdf4; }
.row-revoked { opacity: 0.5; }
.badge {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  margin-left: 0.25rem;
}
.badge-active { background: #d1fae5; color: #065f46; }
.badge-warn { background: #fef3c7; color: #92400e; }
.badge-revoked { background: #f3f4f6; color: #6b7280; }
.badge-current { background: #dbeafe; color: #1e40af; }
.actions { display: flex; gap: 0.5rem; align-items: center; }
.btn-sm {
  padding: 0.25rem 0.625rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  font-size: 0.8rem;
}
.btn-sm:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-sm.btn-danger { background: #dc2626; color: white; border-color: #dc2626; }
.btn-sm.btn-danger:hover:not(:disabled) { background: #b91c1c; }
.btn-secondary {
  padding: 0.5rem 1rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  font-size: 0.875rem;
}
.loading, .empty, .error-msg { padding: 2rem; text-align: center; color: #888; }
.error-msg { color: #dc2626; }
</style>
