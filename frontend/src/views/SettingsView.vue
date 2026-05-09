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

    <!-- Appearance -->
    <section class="settings-section">
      <h2>{{ t('settings.theme') }}</h2>
      <div class="theme-row">
        <span class="info-label">{{ t('settings.darkMode') }}</span>
        <button
          class="theme-toggle"
          :class="{ active: theme === 'dark' }"
          :aria-label="t('settings.toggleTheme')"
          @click="toggleTheme()"
        >
          <span class="toggle-thumb" />
        </button>
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
import { useTheme } from '@/composables/useTheme'

const { t, locale } = useI18n()
const auth = useAuthStore()
const { theme, toggle: toggleTheme } = useTheme()

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
  background: var(--bbf-bg);
  color: var(--bbf-ink);
}

.theme-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.875rem;
}

.theme-toggle {
  width: 40px;
  height: 22px;
  border-radius: 999px;
  background: var(--bbf-line-strong);
  border: none;
  padding: 2px;
  cursor: pointer;
  transition: background 0.2s;
  position: relative;
}
.theme-toggle.active { background: var(--bbf-primary); }

.toggle-thumb {
  display: block;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: white;
  box-shadow: 0 1px 3px rgba(0,0,0,.2);
  transition: transform 0.2s;
  position: absolute;
  top: 2px;
  left: 2px;
}
.theme-toggle.active .toggle-thumb { transform: translateX(18px); }

.page-title {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 2rem;
}

.settings-section {
  background: var(--bbf-surface);
  border: 1px solid var(--bbf-line);
  border-radius: var(--bbf-r-lg);
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.settings-section h2 {
  font-size: 1rem;
  font-weight: 700;
  margin: 0 0 1.25rem;
  color: var(--bbf-ink);
}

.info-grid { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 0; }
.info-row { display: flex; align-items: center; gap: 1rem; font-size: 0.875rem; }
.info-label { color: var(--bbf-ink-3); min-width: 80px; }
.info-value { font-weight: 500; color: var(--bbf-ink); }

.mt { margin-top: 1.25rem; }

.form-group { display: flex; flex-direction: column; gap: 0.375rem; margin-bottom: 1rem; }
.form-group label { font-size: 0.875rem; font-weight: 600; color: var(--bbf-ink-2); }
.form-group input, .select-input {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--bbf-line-strong);
  border-radius: var(--bbf-r-md);
  font-size: 0.875rem;
  max-width: 280px;
  background: var(--bbf-surface-2);
  color: var(--bbf-ink);
  font-family: var(--bbf-font);
}

.settings-form { display: flex; flex-direction: column; }

.badge {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
}
.badge-admin { background: var(--bbf-warn-soft); color: var(--bbf-warn); }
.badge-user { background: var(--bbf-primary-soft); color: var(--bbf-primary-ink); }
.badge-current { background: var(--bbf-info-soft); color: var(--bbf-info); }
.badge-revoked { background: var(--bbf-mute-soft); color: var(--bbf-mute); }

.saved-msg { font-size: 0.8rem; color: var(--bbf-ok); margin-left: 0.75rem; }
.form-error { font-size: 0.875rem; color: var(--bbf-danger); background: var(--bbf-danger-soft); padding: 0.5rem 0.75rem; border-radius: var(--bbf-r-sm); margin-bottom: 0.75rem; }

.btn-primary {
  align-self: flex-start;
  padding: 0.5rem 1.25rem;
  border: none;
  border-radius: var(--bbf-r-md);
  background: var(--bbf-primary);
  color: white;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 600;
  font-family: var(--bbf-font);
}
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

.sessions-list { display: flex; flex-direction: column; gap: 0.75rem; }
.session-card {
  border: 1px solid var(--bbf-line);
  border-radius: var(--bbf-r-md);
  padding: 0.75rem 1rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  font-size: 0.875rem;
  background: var(--bbf-surface);
}
.session-card.current { border-color: var(--bbf-info); background: var(--bbf-info-soft); }
.session-meta { display: flex; align-items: center; gap: 0.5rem; min-width: 140px; }
.session-ip { font-weight: 600; font-family: var(--bbf-mono); color: var(--bbf-ink); }
.session-detail { flex: 1; display: flex; flex-direction: column; gap: 0.125rem; color: var(--bbf-ink-2); font-size: 0.8rem; }
.ua { color: var(--bbf-ink); font-weight: 500; }
.date { color: var(--bbf-ink-3); }
.btn-revoke {
  padding: 0.25rem 0.75rem;
  border: 1px solid var(--bbf-danger);
  border-radius: var(--bbf-r-sm);
  background: var(--bbf-danger-soft);
  color: var(--bbf-danger);
  cursor: pointer;
  font-size: 0.8rem;
  white-space: nowrap;
  font-family: var(--bbf-font);
}
.btn-revoke:hover { background: var(--bbf-danger); color: white; }
.loading, .empty { color: var(--bbf-ink-3); text-align: center; padding: 1rem; font-size: 0.875rem; }
</style>
