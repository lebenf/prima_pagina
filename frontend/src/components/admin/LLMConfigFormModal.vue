<template>
  <Teleport to="body">
    <div class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-dialog" role="dialog" aria-modal="true">
        <div class="modal-header">
          <h3>{{ isEdit ? t('admin.llm.editProvider') : t('admin.llm.addProvider') }}</h3>
          <button class="close-btn" @click="$emit('close')">×</button>
        </div>

        <form @submit.prevent="submit" class="modal-form">
          <div class="form-group">
            <label>Provider *</label>
            <select v-model="form.provider" :disabled="isEdit">
              <option value="ollama">Ollama</option>
              <option value="claude">Claude (Anthropic)</option>
            </select>
          </div>

          <div class="form-group">
            <label>Label</label>
            <input v-model="form.label" type="text" placeholder="Es. Ollama locale" />
          </div>

          <div class="form-group">
            <label>{{ t('admin.llm.model') }} *</label>
            <input v-model="form.model_name" type="text" required list="model-suggestions" placeholder="es. llama3.2" />
            <datalist id="model-suggestions">
              <template v-if="form.provider === 'ollama'">
                <option value="llama3.2" />
                <option value="mistral" />
                <option value="gemma2" />
                <option value="phi3" />
              </template>
              <template v-else>
                <option value="claude-opus-4-5" />
                <option value="claude-sonnet-4-5" />
                <option value="claude-haiku-4-5" />
              </template>
            </datalist>
          </div>

          <div v-if="form.provider === 'ollama'" class="form-group">
            <label>{{ t('admin.llm.endpoint') }}</label>
            <input v-model="form.endpoint_url" type="url" placeholder="http://ollama:11434" />
          </div>

          <div v-if="form.provider === 'claude'" class="form-group">
            <label>{{ t('admin.llm.apiKey') }}{{ isEdit ? ' (lascia vuoto per non cambiare)' : ' *' }}</label>
            <div class="input-with-toggle">
              <input
                v-model="form.api_key"
                :type="showKey ? 'text' : 'password'"
                :required="!isEdit && form.provider === 'claude'"
                placeholder="sk-ant-..."
              />
              <button type="button" class="toggle-btn" @click="showKey = !showKey">
                {{ showKey ? '🙈' : '👁️' }}
              </button>
            </div>
          </div>

          <div class="form-group">
            <label>{{ t('admin.llm.useFor') }}</label>
            <div class="checkbox-group">
              <label><input v-model="form.use_for" type="checkbox" value="tagging" /> Tagging</label>
              <label><input v-model="form.use_for" type="checkbox" value="digest" /> Digest</label>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>{{ t('admin.llm.priority') }}</label>
              <input v-model.number="form.priority" type="number" min="1" max="100" />
            </div>
            <div class="form-group form-group-inline">
              <label>{{ t('admin.llm.isDefault') }}</label>
              <input v-model="form.is_default" type="checkbox" />
            </div>
            <div class="form-group form-group-inline">
              <label>{{ t('admin.users.active') }}</label>
              <input v-model="form.is_active" type="checkbox" />
            </div>
          </div>

          <div v-if="error" class="form-error">{{ error }}</div>

          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="$emit('close')">{{ t('common.cancel') }}</button>
            <button type="submit" class="btn-primary" :disabled="saving">
              {{ saving ? t('common.loading') : t('common.save') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { adminApi, type LLMConfig, type LLMConfigCreate } from '@/api/admin'

const props = defineProps<{ config?: LLMConfig | null }>()
const emit = defineEmits<{ close: []; saved: [config: LLMConfig] }>()
const { t } = useI18n()
const isEdit = computed(() => !!props.config)
const showKey = ref(false)

const defaultForm = (): LLMConfigCreate & { api_key: string } => ({
  provider: 'ollama',
  label: '',
  model_name: '',
  endpoint_url: '',
  api_key: '',
  use_for: [],
  is_default: false,
  is_active: true,
  priority: 10,
})

const form = ref(defaultForm())
const saving = ref(false)
const error = ref('')

watch(() => props.config, (c) => {
  if (c) {
    form.value = {
      provider: c.provider,
      label: c.label || '',
      model_name: c.model_name,
      endpoint_url: c.endpoint_url || '',
      api_key: '',
      use_for: [...c.use_for],
      is_default: c.is_default,
      is_active: c.is_active,
      priority: c.priority,
    }
  } else {
    form.value = defaultForm()
  }
}, { immediate: true })

async function submit() {
  error.value = ''
  saving.value = true
  try {
    const payload: Partial<LLMConfigCreate> = {
      provider: form.value.provider,
      model_name: form.value.model_name,
      use_for: form.value.use_for,
      is_default: form.value.is_default,
      is_active: form.value.is_active,
      priority: form.value.priority,
    }
    if (form.value.label) payload.label = form.value.label
    if (form.value.endpoint_url) payload.endpoint_url = form.value.endpoint_url
    if (form.value.api_key) payload.api_key = form.value.api_key

    if (isEdit.value && props.config) {
      const res = await adminApi.llm.update(props.config.id, payload)
      emit('saved', res.data)
    } else {
      const res = await adminApi.llm.create(payload as LLMConfigCreate)
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
.form-group input[type="text"], .form-group input[type="url"], .form-group input[type="number"], .form-group input[type="password"], .form-group select {
  padding: 0.5rem 0.75rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.875rem;
}
.form-group-inline { flex-direction: row; align-items: center; gap: 0.5rem; }
.form-row { display: flex; gap: 1rem; align-items: flex-end; }
.form-row .form-group { flex: 1; }
.checkbox-group { display: flex; gap: 1rem; }
.checkbox-group label { display: flex; align-items: center; gap: 0.375rem; font-weight: 400; }
.input-with-toggle { display: flex; gap: 0.5rem; }
.input-with-toggle input { flex: 1; }
.toggle-btn { background: none; border: 1px solid #ccc; border-radius: 4px; padding: 0 0.5rem; cursor: pointer; }
.form-error { color: #dc2626; font-size: 0.875rem; padding: 0.5rem; background: #fef2f2; border-radius: 4px; }
.modal-actions { display: flex; gap: 0.75rem; justify-content: flex-end; margin-top: 0.5rem; }
.btn-primary { padding: 0.5rem 1.25rem; border: none; border-radius: 4px; background: #1a1a1a; color: white; cursor: pointer; font-size: 0.875rem; font-weight: 600; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-secondary { padding: 0.5rem 1.25rem; border: 1px solid #ccc; border-radius: 4px; background: white; cursor: pointer; font-size: 0.875rem; }
</style>
