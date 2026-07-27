<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="function-assignments">
    <h2>{{ t('admin.llmFunctions.title') }}</h2>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>
    <table v-else class="function-table">
      <thead>
        <tr>
          <th>{{ t('admin.llmFunctions.function') }}</th>
          <th>{{ t('admin.llmFunctions.primaryProvider') }}</th>
          <th>{{ t('admin.llmFunctions.fallbackProvider') }}</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="row.function">
          <td>
            <strong>{{ t(`admin.llmFunctions.functions.${camelCase(row.function)}`) }}</strong>
          </td>
          <td>
            <select v-model="row.primary_config_id">
              <option :value="null">—</option>
              <option v-for="c in configs" :key="c.id" :value="c.id">{{ providerLabel(c) }}</option>
            </select>
          </td>
          <td>
            <select v-model="row.fallback_config_id">
              <option :value="null">{{ t('admin.llmFunctions.noFallback') }}</option>
              <option v-for="c in configs" :key="c.id" :value="c.id">{{ providerLabel(c) }}</option>
            </select>
          </td>
          <td>
            <button class="btn-sm" :disabled="saving === row.function" @click="save(row)">
              {{ saving === row.function ? t('common.loading') : t('common.save') }}
            </button>
            <span v-if="savedFlash[row.function]" class="saved-flash">✓ {{ t('admin.llmFunctions.saved') }}</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { adminApi, type LLMConfig, type LLMFunctionAssignment } from '@/api/admin'

const props = defineProps<{ configs: LLMConfig[] }>()
const { t } = useI18n()

const rows = ref<LLMFunctionAssignment[]>([])
const loading = ref(false)
const error = ref('')
const saving = ref<string | null>(null)
const savedFlash = reactive<Record<string, boolean>>({})

function camelCase(functionName: string): string {
  return functionName.replace(/_([a-z])/g, (_, c) => c.toUpperCase())
}

function providerLabel(c: LLMConfig): string {
  return `${c.provider} — ${c.model_name}${c.label ? ` (${c.label})` : ''}`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await adminApi.llmFunctions.list()
    rows.value = res.data
  } catch {
    error.value = t('common.error')
  } finally {
    loading.value = false
  }
}

async function save(row: LLMFunctionAssignment) {
  saving.value = row.function
  try {
    await adminApi.llmFunctions.update(row.function, {
      primary_config_id: row.primary_config_id,
      fallback_config_id: row.fallback_config_id,
    })
    savedFlash[row.function] = true
    setTimeout(() => { savedFlash[row.function] = false }, 2000)
  } catch {
    error.value = t('common.error')
  } finally {
    saving.value = null
  }
}

onMounted(load)
</script>

<style scoped>
.function-assignments { margin-bottom: 2rem; }
.function-assignments h2 { font-size: 1.25rem; font-weight: 700; margin: 0 0 1rem; }
.function-table { width: 100%; border-collapse: collapse; }
.function-table th, .function-table td { padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid #eee; font-size: 0.875rem; }
.function-table select { padding: 0.375rem 0.5rem; border: 1px solid #ccc; border-radius: 4px; font-size: 0.85rem; max-width: 260px; }
.btn-sm { padding: 0.375rem 0.75rem; border: 1px solid #ccc; border-radius: 4px; background: white; cursor: pointer; font-size: 0.8rem; }
.btn-sm:disabled { opacity: 0.5; cursor: not-allowed; }
.saved-flash { margin-left: 0.5rem; color: #16a34a; font-size: 0.8rem; font-weight: 600; }
.loading, .error-msg { padding: 1rem; text-align: center; color: #888; }
.error-msg { color: #dc2626; }
</style>
