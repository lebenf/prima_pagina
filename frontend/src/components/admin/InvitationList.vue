<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="invitation-section">
    <div class="section-subheader">
      <h3>{{ t('admin.users.invitations') }}</h3>
      <button class="btn-sm" @click="showCreateForm = !showCreateForm">
        + {{ t('admin.users.createInvite') }}
      </button>
    </div>

    <div v-if="showCreateForm" class="invite-form">
      <input
        v-model="newEmail"
        type="email"
        :placeholder="t('admin.users.inviteEmailPlaceholder')"
        class="invite-input"
      />
      <button @click="submitInvite" :disabled="creating" class="btn-sm btn-primary">
        {{ creating ? t('common.loading') : t('admin.users.generateLink') }}
      </button>
    </div>

    <div v-if="generatedLink" class="invite-link-box">
      <input :value="generatedLink" readonly class="link-input" />
      <button @click="copyLink" class="btn-sm">
        {{ copied ? '✓ ' + t('common.copied') : t('common.copyLink') }}
      </button>
    </div>

    <div v-if="loading" class="loading-sm">{{ t('common.loading') }}</div>
    <div v-else-if="invitations.length === 0" class="empty-msg">—</div>
    <table v-else class="invite-table">
      <thead>
        <tr>
          <th>Email</th>
          <th>{{ t('admin.feeds.neverFetched') !== 'Nunca' ? 'Scade' : 'Vence' }}</th>
          <th>Stato</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="inv in invitations" :key="inv.id">
          <td>{{ inv.email || '—' }}</td>
          <td class="expires-col">{{ formatDate(inv.expires_at) }}</td>
          <td>
            <span :class="['invite-badge', inviteStatusClass(inv)]">
              {{ inviteStatusLabel(inv) }}
            </span>
          </td>
          <td>
            <button
              v-if="inv.is_valid"
              class="btn-danger-sm"
              @click="revokeInvite(inv.id)"
            >Revoca</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { adminApi, type Invitation } from '@/api/admin'

const { t } = useI18n()

const invitations = ref<Invitation[]>([])
const loading = ref(false)
const showCreateForm = ref(false)
const newEmail = ref('')
const creating = ref(false)
const generatedLink = ref<string | null>(null)
const copied = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await adminApi.invitations.list()
    invitations.value = res.data
  } catch {
    /* silent */
  } finally {
    loading.value = false
  }
}

async function submitInvite() {
  creating.value = true
  try {
    const res = await adminApi.invitations.create(
      newEmail.value ? { email: newEmail.value } : {}
    )
    generatedLink.value = res.data.invite_url
    invitations.value.unshift(res.data)
    showCreateForm.value = false
    newEmail.value = ''
  } catch {
    /* silent */
  } finally {
    creating.value = false
  }
}

async function copyLink() {
  if (!generatedLink.value) return
  try {
    await navigator.clipboard.writeText(generatedLink.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    /* Clipboard API not available — user can select the input manually */
  }
}

async function revokeInvite(id: string) {
  await adminApi.invitations.revoke(id)
  invitations.value = invitations.value.map(i =>
    i.id === id ? { ...i, is_valid: false, used_at: new Date().toISOString() } : i
  )
}

function inviteStatusClass(inv: Invitation): string {
  if (inv.used_at) return 'used'
  if (!inv.is_valid) return 'expired'
  return 'active'
}

function inviteStatusLabel(inv: Invitation): string {
  if (inv.used_at) return t('admin.users.inviteStatusUsed')
  if (!inv.is_valid) return t('admin.users.inviteStatusExpired')
  return t('admin.users.inviteStatusActive')
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString()
}

onMounted(load)
</script>

<style scoped>
.invitation-section {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e5e5e5;
}

.section-subheader {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.section-subheader h3 {
  font-size: 1rem;
  font-weight: 700;
  margin: 0;
}

.invite-form {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.invite-input {
  flex: 1;
  padding: 0.375rem 0.75rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.875rem;
}

.invite-link-box {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.75rem;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 4px;
  padding: 0.5rem 0.75rem;
}

.link-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 0.8rem;
  font-family: monospace;
  color: #166534;
}

.invite-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
}

.invite-table th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #e5e5e5;
  color: #6b7280;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.invite-table td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #f3f4f6;
}

.expires-col {
  color: #6b7280;
  font-size: 0.75rem;
}

.invite-badge {
  display: inline-block;
  padding: 0.1rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.invite-badge.active { background: #d1fae5; color: #065f46; }
.invite-badge.expired { background: #f3f4f6; color: #6b7280; }
.invite-badge.used { background: #e0e7ff; color: #3730a3; }

.btn-sm {
  padding: 0.25rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  font-size: 0.8rem;
  white-space: nowrap;
}

.btn-sm.btn-primary {
  background: #1a1a1a;
  color: white;
  border-color: #1a1a1a;
}

.btn-danger-sm {
  padding: 0.1rem 0.5rem;
  border: 1px solid #fca5a5;
  border-radius: 4px;
  background: #fef2f2;
  color: #dc2626;
  cursor: pointer;
  font-size: 0.75rem;
}

.loading-sm, .empty-msg {
  font-size: 0.875rem;
  color: #9ca3af;
  padding: 0.5rem 0;
}
</style>
