<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <Teleport to="body">
    <div class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-dialog" role="dialog" aria-modal="true">
        <div class="modal-header">
          <h3>{{ isEdit ? t('admin.plugins.editPlugin') : t('admin.plugins.addPlugin') }}</h3>
          <button class="close-btn" @click="$emit('close')">×</button>
        </div>

        <form @submit.prevent="submit" class="modal-form">
          <div class="form-group">
            <label>Tipo plugin *</label>
            <select v-model="selectedType" :disabled="isEdit" @change="onTypeChange">
              <option value="">— seleziona —</option>
              <option v-for="p in available" :key="p.plugin_type" :value="p.plugin_type">
                {{ p.label }}
              </option>
            </select>
          </div>

          <div class="form-group">
            <label>Label</label>
            <input v-model="form.label" type="text" placeholder="Es. Canale notizie" />
          </div>

          <template v-if="pluginFields.length > 0">
            <div v-for="field in pluginFields" :key="field.key" class="form-group">
              <label>{{ field.label }}{{ field.required ? ' *' : '' }}</label>
              <template v-if="field.type === 'multiselect'">
                <div class="checkbox-group">
                  <label v-for="opt in field.options || []" :key="opt">
                    <input
                      type="checkbox"
                      :value="opt"
                      :checked="(configValues[field.key] as string[] || []).includes(opt)"
                      @change="toggleMultiselect(field.key, opt, ($event.target as HTMLInputElement).checked)"
                    />
                    {{ opt }}
                  </label>
                </div>
              </template>
              <input
                v-else
                v-model="configValues[field.key]"
                :type="field.type"
                :required="field.required && !isEdit"
                :placeholder="field.secret ? '••••••••' : field.label"
              />
              <small v-if="field.description" class="hint">{{ field.description }}</small>
            </div>
          </template>

          <div class="form-group form-group-inline">
            <label>{{ t('admin.users.active') }}</label>
            <input v-model="form.is_active" type="checkbox" />
          </div>

          <div v-if="error" class="form-error">{{ error }}</div>

          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="$emit('close')">{{ t('common.cancel') }}</button>
            <button type="submit" class="btn-primary" :disabled="saving || !selectedType">
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
import { adminApi, type PluginConfig, type PluginAvailable } from '@/api/admin'

const props = defineProps<{
  plugin?: PluginConfig | null
  available: PluginAvailable[]
}>()

const emit = defineEmits<{
  close: []
  saved: [plugin: PluginConfig]
}>()

const { t } = useI18n()
const isEdit = computed(() => !!props.plugin)

const selectedType = ref('')
const configValues = ref<Record<string, any>>({})
const form = ref({ label: '', is_active: true })
const saving = ref(false)
const error = ref('')

const selectedPlugin = computed(() =>
  props.available.find(p => p.plugin_type === selectedType.value)
)

const pluginFields = computed(() => {
  const schema = selectedPlugin.value?.config_schema
  if (!schema) return []
  return Object.entries(schema).map(([key, meta]) => {
    let type = 'text'
    if (meta.type === 'list') type = 'multiselect'
    else if (meta.secret) type = 'password'

    let options: string[] | undefined
    if (meta.type === 'list' && Array.isArray(meta.default)) {
      // derive options from context — for notify_events use known values
      options = ['new_article', 'digest_ready', 'feed_error', 'system']
    }

    return { key, label: meta.label, type, required: meta.required, secret: meta.secret, description: meta.description, options }
  })
})

watch(() => props.plugin, (p) => {
  if (p) {
    selectedType.value = p.plugin_type
    form.value = { label: p.label || '', is_active: p.is_active }
    configValues.value = {}
  } else {
    selectedType.value = ''
    form.value = { label: '', is_active: true }
    configValues.value = {}
  }
}, { immediate: true })

function onTypeChange() {
  configValues.value = {}
  // Set defaults from schema
  const schema = selectedPlugin.value?.config_schema
  if (schema) {
    for (const [key, meta] of Object.entries(schema)) {
      if (meta.default !== undefined) {
        configValues.value[key] = meta.default
      }
    }
  }
}

function toggleMultiselect(key: string, value: string, checked: boolean) {
  const arr: string[] = Array.isArray(configValues.value[key]) ? [...configValues.value[key]] : []
  if (checked) {
    if (!arr.includes(value)) arr.push(value)
  } else {
    const idx = arr.indexOf(value)
    if (idx >= 0) arr.splice(idx, 1)
  }
  configValues.value[key] = arr
}

async function submit() {
  error.value = ''
  saving.value = true
  try {
    const config_json = { ...configValues.value }
    const payload = {
      plugin_type: selectedType.value,
      label: form.value.label || undefined,
      config_json,
      is_active: form.value.is_active,
    }
    if (isEdit.value && props.plugin) {
      const res = await adminApi.plugins.update(props.plugin.id, payload)
      emit('saved', res.data)
    } else {
      const res = await adminApi.plugins.create(payload)
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
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 900; }
.modal-dialog { background: white; border-radius: 8px; width: 90%; max-width: 520px; box-shadow: 0 8px 32px rgba(0,0,0,0.2); max-height: 90vh; overflow-y: auto; }
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 1.25rem 1.5rem; border-bottom: 1px solid #e5e5e5; }
.modal-header h3 { margin: 0; font-size: 1.1rem; font-weight: 700; }
.close-btn { background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #666; }
.modal-form { padding: 1.5rem; display: flex; flex-direction: column; gap: 1rem; }
.form-group { display: flex; flex-direction: column; gap: 0.25rem; }
.form-group label { font-size: 0.875rem; font-weight: 600; color: #444; }
.form-group input[type="text"], .form-group input[type="password"], .form-group select {
  padding: 0.5rem 0.75rem; border: 1px solid #ccc; border-radius: 4px; font-size: 0.875rem;
}
.form-group-inline { flex-direction: row; align-items: center; gap: 0.5rem; }
.checkbox-group { display: flex; gap: 1rem; flex-wrap: wrap; }
.checkbox-group label { display: flex; align-items: center; gap: 0.375rem; font-weight: 400; }
.hint { font-size: 0.75rem; color: #888; }
.form-error { color: #dc2626; font-size: 0.875rem; padding: 0.5rem; background: #fef2f2; border-radius: 4px; }
.modal-actions { display: flex; gap: 0.75rem; justify-content: flex-end; margin-top: 0.5rem; }
.btn-primary { padding: 0.5rem 1.25rem; border: none; border-radius: 4px; background: #1a1a1a; color: white; cursor: pointer; font-size: 0.875rem; font-weight: 600; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-secondary { padding: 0.5rem 1.25rem; border: 1px solid #ccc; border-radius: 4px; background: white; cursor: pointer; font-size: 0.875rem; }
</style>
