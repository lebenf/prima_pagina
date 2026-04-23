<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="admin-section">
    <div class="section-header">
      <h2>{{ t('admin.plugins.title') }}</h2>
      <button class="btn-primary" @click="openCreate">+ {{ t('admin.plugins.addPlugin') }}</button>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>
    <div v-else class="plugin-list">
      <div v-for="plugin in plugins" :key="plugin.id" class="plugin-card">
        <div class="card-header">
          <div class="card-title">
            <span class="plugin-icon">📨</span>
            <strong>{{ pluginLabel(plugin) }}</strong>
            <span class="plugin-type">— {{ plugin.plugin_type }}</span>
            <span v-if="!plugin.is_active" class="badge badge-inactive">Inattivo</span>
          </div>
        </div>

        <div class="card-body">
          <div class="card-meta">
            {{ plugin.user_id ? t('admin.plugins.userScope') : t('admin.plugins.globalScope') }}
          </div>
          <div class="card-meta">
            Config: {{ plugin.has_config ? '✓' : '✗' }}
          </div>

          <div v-if="testResults[plugin.id]" :class="['test-result', testResults[plugin.id].ok ? 'test-ok' : 'test-fail']">
            {{ testResults[plugin.id].ok ? '✅' : '❌' }}
            {{ testResults[plugin.id].message }}
            <span v-if="testResults[plugin.id].latency_ms">({{ testResults[plugin.id].latency_ms }}ms)</span>
          </div>
        </div>

        <div class="card-actions">
          <button
            class="btn-sm"
            :disabled="testing === plugin.id"
            @click="runTest(plugin.id)"
          >
            {{ testing === plugin.id ? t('admin.plugins.testing') : '🔍 ' + t('admin.plugins.testConnection') }}
          </button>
          <button class="btn-sm" @click="openEdit(plugin)">✏️</button>
          <button class="btn-sm btn-danger" @click="confirmDelete(plugin)">🗑️</button>
        </div>
      </div>

      <div v-if="plugins.length === 0" class="empty">
        Nessun plugin configurato.
      </div>
    </div>

    <PluginFormModal
      v-if="showModal"
      :plugin="editingPlugin"
      :available="available"
      @close="showModal = false"
      @saved="onSaved"
    />

    <ConfirmDialog
      v-if="showConfirm"
      :title="t('common.delete')"
      :message="t('admin.plugins.deleteConfirm', { label: pluginLabel(deletingPlugin!) })"
      @confirm="doDelete"
      @cancel="showConfirm = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { adminApi, type PluginConfig, type PluginAvailable } from '@/api/admin'
import PluginFormModal from './PluginFormModal.vue'
import ConfirmDialog from './ConfirmDialog.vue'

const { t } = useI18n()

const plugins = ref<PluginConfig[]>([])
const available = ref<PluginAvailable[]>([])
const loading = ref(false)
const error = ref('')
const showModal = ref(false)
const editingPlugin = ref<PluginConfig | null>(null)
const showConfirm = ref(false)
const deletingPlugin = ref<PluginConfig | null>(null)
const testing = ref<string | null>(null)
const testResults = reactive<Record<string, { ok: boolean; message: string; latency_ms: number }>>({})

function pluginLabel(plugin: PluginConfig) {
  return plugin.label || plugin.plugin_type
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [pluginsRes, availableRes] = await Promise.all([
      adminApi.plugins.list(),
      adminApi.plugins.available(),
    ])
    plugins.value = pluginsRes.data
    available.value = availableRes.data
  } catch {
    error.value = t('common.error')
  } finally {
    loading.value = false
  }
}

async function runTest(id: string) {
  testing.value = id
  try {
    const res = await adminApi.plugins.test(id)
    testResults[id] = res.data
  } catch (e: any) {
    testResults[id] = { ok: false, message: e.response?.data?.detail || 'Errore', latency_ms: 0 }
  } finally {
    testing.value = null
  }
}

function openCreate() { editingPlugin.value = null; showModal.value = true }
function openEdit(plugin: PluginConfig) { editingPlugin.value = plugin; showModal.value = true }
function confirmDelete(plugin: PluginConfig) { deletingPlugin.value = plugin; showConfirm.value = true }

async function doDelete() {
  if (!deletingPlugin.value) return
  try {
    await adminApi.plugins.delete(deletingPlugin.value.id)
    plugins.value = plugins.value.filter(p => p.id !== deletingPlugin.value!.id)
  } catch {
    error.value = t('common.error')
  } finally {
    showConfirm.value = false
    deletingPlugin.value = null
  }
}

function onSaved(plugin: PluginConfig) {
  const idx = plugins.value.findIndex(p => p.id === plugin.id)
  if (idx >= 0) { plugins.value[idx] = plugin } else { plugins.value.push(plugin) }
  showModal.value = false
}

onMounted(load)
</script>

<style scoped>
.admin-section { padding: 1.5rem; }
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.25rem; }
.section-header h2 { font-size: 1.25rem; font-weight: 700; margin: 0; }
.plugin-list { display: flex; flex-direction: column; gap: 1rem; }
.plugin-card { border: 1px solid #e5e5e5; border-radius: 8px; overflow: hidden; }
.card-header { padding: 1rem 1.25rem; background: #fafafa; border-bottom: 1px solid #e5e5e5; }
.card-title { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.plugin-icon { font-size: 1.25rem; }
.plugin-type { color: #666; font-size: 0.9rem; }
.card-body { padding: 0.75rem 1.25rem; }
.card-meta { font-size: 0.875rem; color: #555; margin-bottom: 0.25rem; }
.card-actions { padding: 0.75rem 1.25rem; display: flex; gap: 0.5rem; flex-wrap: wrap; border-top: 1px solid #f0f0f0; }
.badge { display: inline-block; padding: 0.125rem 0.5rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; }
.badge-inactive { background: #f3f4f6; color: #6b7280; }
.test-result { margin-top: 0.5rem; padding: 0.375rem 0.75rem; border-radius: 4px; font-size: 0.875rem; font-weight: 500; }
.test-ok { background: #d1fae5; color: #065f46; }
.test-fail { background: #fee2e2; color: #991b1b; }
.btn-sm { padding: 0.375rem 0.75rem; border: 1px solid #ccc; border-radius: 4px; background: white; cursor: pointer; font-size: 0.8rem; }
.btn-sm:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-sm.btn-danger { background: #fee2e2; border-color: #fca5a5; color: #991b1b; }
.btn-sm.btn-danger:hover { background: #fecaca; }
.btn-primary { padding: 0.5rem 1rem; border: none; border-radius: 4px; background: #1a1a1a; color: white; cursor: pointer; font-size: 0.875rem; font-weight: 600; }
.loading, .empty, .error-msg { padding: 2rem; text-align: center; color: #888; }
.error-msg { color: #dc2626; }
</style>
