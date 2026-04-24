<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="settings-page">
    <h1 class="page-title">{{ t('nav.settings') }}</h1>

    <!-- Profile -->
    <section class="settings-section">
      <h2>{{ t('settings.profile') }}</h2>
      <div class="info-grid">
        <div class="info-row">
          <span class="info-label">Username</span>
          <span class="info-value">{{ auth.user?.username }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Email</span>
          <span class="info-value">{{ auth.user?.email }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">{{ t('settings.role') }}</span>
          <span class="info-value">
            <span :class="['badge', auth.user?.role === 'admin' ? 'badge-admin' : 'badge-user']">
              {{ auth.user?.role }}
            </span>
          </span>
        </div>
      </div>

      <div class="form-group mt">
        <label>{{ t('settings.language') }}</label>
        <select v-model="selectedLang" @change="saveLang" class="select-input">
          <option value="it">Italiano</option>
          <option value="en">English</option>
          <option value="fr">Français</option>
          <option value="de">Deutsch</option>
          <option value="es">Español</option>
          <option value="pt">Português</option>
        </select>
        <span v-if="langSaved" class="saved-msg">✓ {{ t('common.saved') }}</span>
      </div>
    </section>

    <!-- Password -->
    <section class="settings-section">
      <h2>{{ t('settings.changePassword') }}</h2>
      <form @submit.prevent="submitPassword" class="settings-form">
        <div class="form-group">
          <label>{{ t('settings.currentPassword') }}</label>
          <input v-model="pw.current" type="password" autocomplete="current-password" required />
        </div>
        <div class="form-group">
          <label>{{ t('settings.newPassword') }}</label>
          <input v-model="pw.next" type="password" autocomplete="new-password" minlength="8" required />
        </div>
        <div class="form-group">
          <label>{{ t('settings.confirmPassword') }}</label>
          <input v-model="pw.confirm" type="password" autocomplete="new-password" required />
        </div>
        <div v-if="pwError" class="form-error">{{ pwError }}</div>
        <div v-if="pwSuccess" class="saved-msg">✓ {{ t('settings.passwordChanged') }}</div>
        <button type="submit" class="btn-primary" :disabled="pwSaving">
          {{ pwSaving ? t('common.loading') : t('settings.changePassword') }}
        </button>
      </form>
    </section>

    <!-- Sessions -->
    <section class="settings-section">
      <h2>{{ t('settings.sessions') }}</h2>
      <div v-if="sessionsLoading" class="loading">{{ t('common.loading') }}</div>
      <div v-else-if="sessions.length === 0" class="empty">{{ t('settings.noSessions') }}</div>
      <div v-else class="sessions-list">
        <div v-for="s in sessions" :key="s.id" class="session-card" :class="{ current: s.is_current }">
          <div class="session-meta">
            <span class="session-ip">{{ s.ip_address || '—' }}</span>
            <span v-if="s.is_current" class="badge badge-current">{{ t('settings.currentSession') }}</span>
            <span v-else-if="s.is_revoked" class="badge badge-revoked">{{ t('settings.revoked') }}</span>
          </div>
          <div class="session-detail">
            <span class="ua">{{ shortUa(s.user_agent) }}</span>
            <span class="date">{{ t('settings.lastActive') }}: {{ fmt(s.last_active_at) }}</span>
            <span class="date">{{ t('settings.expires') }}: {{ fmt(s.expires_at) }}</span>
          </div>
          <button
            v-if="!s.is_current && !s.is_revoked"
            class="btn-revoke"
            @click="revoke(s.id)"
          >{{ t('settings.revoke') }}</button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { authApi, type Session } from '@/api/auth'

const { t, locale } = useI18n()
const auth = useAuthStore()

// ── Language ──────────────────────────────────────────────
const selectedLang = ref(auth.user?.preferred_lang || 'it')
const langSaved = ref(false)
let langTimer: ReturnType<typeof setTimeout> | null = null

async function saveLang() {
  try {
    const res = await authApi.updateMe({ preferred_lang: selectedLang.value })
    auth.user = res.data
    locale.value = selectedLang.value
    langSaved.value = true
    if (langTimer) clearTimeout(langTimer)
    langTimer = setTimeout(() => { langSaved.value = false }, 2000)
  } catch { /* ignore */ }
}

// ── Password ──────────────────────────────────────────────
const pw = ref({ current: '', next: '', confirm: '' })
const pwError = ref('')
const pwSuccess = ref(false)
const pwSaving = ref(false)

async function submitPassword() {
  pwError.value = ''
  pwSuccess.value = false
  if (pw.value.next !== pw.value.confirm) {
    pwError.value = t('settings.passwordMismatch')
    return
  }
  pwSaving.value = true
  try {
    await authApi.updatePassword(pw.value.current, pw.value.next)
    pw.value = { current: '', next: '', confirm: '' }
    pwSuccess.value = true
  } catch (e: any) {
    pwError.value = e.response?.data?.detail || t('common.error')
  } finally {
    pwSaving.value = false
  }
}

// ── Sessions ──────────────────────────────────────────────
const sessions = ref<Session[]>([])
const sessionsLoading = ref(false)

async function loadSessions() {
  sessionsLoading.value = true
  try {
    const res = await authApi.sessions()
    sessions.value = res.data.sort((a, b) =>
      new Date(b.last_active_at).getTime() - new Date(a.last_active_at).getTime()
    )
  } finally {
    sessionsLoading.value = false
  }
}

async function revoke(id: string) {
  try {
    await authApi.revokeSession(id)
    const s = sessions.value.find(x => x.id === id)
    if (s) (s as any).is_revoked = true
  } catch { /* ignore */ }
}

function fmt(iso: string) {
  return new Date(iso).toLocaleString()
}

function shortUa(ua: string | null) {
  if (!ua) return '—'
  const m = ua.match(/(Firefox|Chrome|Safari|Edge|Opera)\/[\d.]+/)
  return m ? m[0] : ua.slice(0, 40)
}

onMounted(loadSessions)
</script>

<style scoped>
.settings-page {
  max-width: 640px;
  margin: 0 auto;
  padding: 2rem 1.5rem;
}

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 2rem;
}

.settings-section {
  background: white;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.settings-section h2 {
  font-size: 1rem;
  font-weight: 700;
  margin: 0 0 1.25rem;
  color: #111;
}

.info-grid { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 0; }
.info-row { display: flex; align-items: center; gap: 1rem; font-size: 0.875rem; }
.info-label { color: #666; min-width: 80px; }
.info-value { font-weight: 500; }

.mt { margin-top: 1.25rem; }

.form-group { display: flex; flex-direction: column; gap: 0.375rem; margin-bottom: 1rem; }
.form-group label { font-size: 0.875rem; font-weight: 600; color: #444; }
.form-group input, .select-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.875rem;
  max-width: 280px;
}

.settings-form { display: flex; flex-direction: column; }

.badge {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
}
.badge-admin { background: #fef3c7; color: #92400e; }
.badge-user { background: #e0e7ff; color: #3730a3; }
.badge-current { background: #dbeafe; color: #1e40af; }
.badge-revoked { background: #f3f4f6; color: #6b7280; }

.saved-msg { font-size: 0.8rem; color: #059669; margin-left: 0.75rem; }
.form-error { font-size: 0.875rem; color: #dc2626; background: #fef2f2; padding: 0.5rem 0.75rem; border-radius: 4px; margin-bottom: 0.75rem; }

.btn-primary {
  align-self: flex-start;
  padding: 0.5rem 1.25rem;
  border: none;
  border-radius: 4px;
  background: #1a1a1a;
  color: white;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 600;
}
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

.sessions-list { display: flex; flex-direction: column; gap: 0.75rem; }
.session-card {
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  padding: 0.75rem 1rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  font-size: 0.875rem;
}
.session-card.current { border-color: #93c5fd; background: #eff6ff; }
.session-meta { display: flex; align-items: center; gap: 0.5rem; min-width: 140px; }
.session-ip { font-weight: 600; font-family: monospace; }
.session-detail { flex: 1; display: flex; flex-direction: column; gap: 0.125rem; color: #555; font-size: 0.8rem; }
.ua { color: #333; font-weight: 500; }
.date { color: #888; }
.btn-revoke {
  padding: 0.25rem 0.75rem;
  border: 1px solid #fca5a5;
  border-radius: 4px;
  background: #fef2f2;
  color: #dc2626;
  cursor: pointer;
  font-size: 0.8rem;
  white-space: nowrap;
}
.btn-revoke:hover { background: #fee2e2; }
.loading, .empty { color: #888; text-align: center; padding: 1rem; font-size: 0.875rem; }
</style>
