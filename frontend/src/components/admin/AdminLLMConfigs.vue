<template>
  <div class="admin-section">
    <div class="section-header">
      <h2>{{ t('admin.llm.title') }}</h2>
      <button class="btn-primary" @click="openCreate">+ {{ t('admin.llm.addProvider') }}</button>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>
    <div v-else class="config-list">
      <div v-for="config in configs" :key="config.id" class="config-card">
        <div class="card-header">
          <div class="card-title">
            <span class="provider-icon">🤖</span>
            <strong>{{ config.label || config.provider }}</strong>
            <span class="model-name">— {{ config.model_name }}</span>
            <span v-if="config.is_default" class="badge badge-default">DEFAULT</span>
            <span v-if="!config.is_active" class="badge badge-inactive">Inattivo</span>
          </div>
        </div>

        <div class="card-body">
          <div class="card-meta">
            <span v-if="config.endpoint_url">{{ config.endpoint_url }}</span>
            <span v-else>Anthropic API</span>
            <span class="separator">·</span>
            <span>{{ t('admin.llm.priority') }}: {{ config.priority }}</span>
            <span class="separator">·</span>
            <span>
              <span v-if="config.provider === 'claude'">
                {{ config.has_api_key ? t('admin.llm.hasApiKey') + ' ✓' : t('admin.llm.noApiKey') + ' ✗' }}
              </span>
            </span>
          </div>
          <div class="card-meta">
            {{ t('admin.llm.useFor') }}: {{ config.use_for.join(', ') || '—' }}
          </div>

          <div v-if="healthResults[config.id]" :class="['health-result', healthResults[config.id].ok ? 'health-ok' : 'health-fail']">
            {{ healthResults[config.id].ok ? '✅' : '❌' }}
            {{ healthResults[config.id].ok
              ? `OK (${healthResults[config.id].latency_ms}ms)`
              : healthResults[config.id].error }}
          </div>
        </div>

        <div class="card-actions">
          <button
            class="btn-sm"
            :disabled="checking === config.id"
            @click="runHealthCheck(config.id)"
          >
            {{ checking === config.id ? t('admin.llm.checking') : '🔍 ' + t('admin.llm.healthCheck') }}
          </button>
          <button class="btn-sm" @click="openEdit(config)">✏️ {{ t('admin.llm.editProvider') }}</button>
          <button class="btn-sm btn-danger" @click="confirmDelete(config)">🗑️ {{ t('common.delete') }}</button>
        </div>
      </div>

      <div v-if="configs.length === 0" class="empty">
        Nessun provider LLM configurato.
      </div>
    </div>

    <LLMConfigFormModal
      v-if="showModal"
      :config="editingConfig"
      @close="showModal = false"
      @saved="onSaved"
    />

    <ConfirmDialog
      v-if="showConfirm"
      :title="t('common.delete')"
      :message="t('admin.llm.deleteConfirm', { label: deletingConfig?.label || deletingConfig?.provider })"
      @confirm="doDelete"
      @cancel="showConfirm = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { adminApi, type LLMConfig } from '@/api/admin'
import LLMConfigFormModal from './LLMConfigFormModal.vue'
import ConfirmDialog from './ConfirmDialog.vue'

const { t } = useI18n()

const configs = ref<LLMConfig[]>([])
const loading = ref(false)
const error = ref('')
const showModal = ref(false)
const editingConfig = ref<LLMConfig | null>(null)
const showConfirm = ref(false)
const deletingConfig = ref<LLMConfig | null>(null)
const checking = ref<string | null>(null)
const healthResults = reactive<Record<string, { ok: boolean; latency_ms: number; error: string | null }>>({})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await adminApi.llm.list()
    configs.value = res.data
  } catch {
    error.value = t('common.error')
  } finally {
    loading.value = false
  }
}

async function runHealthCheck(id: string) {
  checking.value = id
  try {
    const res = await adminApi.llm.healthCheck(id)
    healthResults[id] = res.data
  } catch (e: any) {
    healthResults[id] = { ok: false, latency_ms: 0, error: e.response?.data?.detail || 'Errore' }
  } finally {
    checking.value = null
  }
}

function openCreate() { editingConfig.value = null; showModal.value = true }
function openEdit(config: LLMConfig) { editingConfig.value = config; showModal.value = true }
function confirmDelete(config: LLMConfig) { deletingConfig.value = config; showConfirm.value = true }

async function doDelete() {
  if (!deletingConfig.value) return
  try {
    await adminApi.llm.delete(deletingConfig.value.id)
    configs.value = configs.value.filter(c => c.id !== deletingConfig.value!.id)
  } catch {
    error.value = t('common.error')
  } finally {
    showConfirm.value = false
    deletingConfig.value = null
  }
}

function onSaved(config: LLMConfig) {
  const idx = configs.value.findIndex(c => c.id === config.id)
  if (idx >= 0) { configs.value[idx] = config } else { configs.value.push(config) }
  showModal.value = false
}

onMounted(load)
</script>

<style scoped>
.admin-section { padding: 1.5rem; }
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.25rem; }
.section-header h2 { font-size: 1.25rem; font-weight: 700; margin: 0; }
.config-list { display: flex; flex-direction: column; gap: 1rem; }
.config-card { border: 1px solid #e5e5e5; border-radius: 8px; overflow: hidden; }
.card-header { padding: 1rem 1.25rem; background: #fafafa; border-bottom: 1px solid #e5e5e5; }
.card-title { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.provider-icon { font-size: 1.25rem; }
.model-name { color: #666; font-size: 0.9rem; }
.card-body { padding: 0.75rem 1.25rem; }
.card-meta { font-size: 0.875rem; color: #555; margin-bottom: 0.25rem; }
.separator { margin: 0 0.25rem; color: #ccc; }
.card-actions { padding: 0.75rem 1.25rem; display: flex; gap: 0.5rem; flex-wrap: wrap; border-top: 1px solid #f0f0f0; }
.badge { display: inline-block; padding: 0.125rem 0.5rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; }
.badge-default { background: #fef3c7; color: #92400e; }
.badge-inactive { background: #f3f4f6; color: #6b7280; }
.health-result { margin-top: 0.5rem; padding: 0.375rem 0.75rem; border-radius: 4px; font-size: 0.875rem; font-weight: 500; }
.health-ok { background: #d1fae5; color: #065f46; }
.health-fail { background: #fee2e2; color: #991b1b; }
.btn-sm { padding: 0.375rem 0.75rem; border: 1px solid #ccc; border-radius: 4px; background: white; cursor: pointer; font-size: 0.8rem; }
.btn-sm:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-sm.btn-danger { background: #fee2e2; border-color: #fca5a5; color: #991b1b; }
.btn-sm.btn-danger:hover { background: #fecaca; }
.btn-primary { padding: 0.5rem 1rem; border: none; border-radius: 4px; background: #1a1a1a; color: white; cursor: pointer; font-size: 0.875rem; font-weight: 600; }
.loading, .empty, .error-msg { padding: 2rem; text-align: center; color: #888; }
.error-msg { color: #dc2626; }
</style>
