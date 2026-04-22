<template>
  <Teleport to="body">
    <div class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-dialog" role="dialog" aria-modal="true">
        <div class="modal-header">
          <h3>{{ isEdit ? t('admin.categories.editCategory') : t('admin.categories.addCategory') }}</h3>
          <button class="close-btn" @click="$emit('close')">×</button>
        </div>

        <form @submit.prevent="submit" class="modal-form">
          <div class="form-group">
            <label>{{ t('admin.categories.slug') }} *</label>
            <input v-model="form.slug" type="text" required placeholder="politics" pattern="[a-z0-9-]+" />
            <small class="hint">Solo lettere minuscole, numeri e trattini</small>
          </div>

          <div class="form-group">
            <label>{{ t('admin.categories.names') }}</label>
            <div class="lang-grid">
              <div v-for="lang in langs" :key="lang.code" class="lang-row">
                <span class="lang-code">{{ lang.code.toUpperCase() }}</span>
                <input v-model="form.name[lang.code]" type="text" :placeholder="lang.label" />
              </div>
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
import { adminApi, type AdminCategory } from '@/api/admin'

const props = defineProps<{ category?: AdminCategory | null }>()
const emit = defineEmits<{ close: []; saved: [cat: AdminCategory] }>()
const { t } = useI18n()
const isEdit = computed(() => !!props.category)

const langs = [
  { code: 'it', label: 'Italiano' },
  { code: 'en', label: 'English' },
  { code: 'fr', label: 'Français' },
  { code: 'de', label: 'Deutsch' },
  { code: 'es', label: 'Español' },
  { code: 'pt', label: 'Português' },
]

const defaultForm = () => ({ slug: '', name: {} as Record<string, string> })
const form = ref(defaultForm())
const saving = ref(false)
const error = ref('')

watch(() => props.category, (c) => {
  if (c) {
    form.value = { slug: c.slug, name: { ...c.name } }
  } else {
    form.value = defaultForm()
  }
}, { immediate: true })

async function submit() {
  error.value = ''
  saving.value = true
  try {
    const payload = { slug: form.value.slug, name: form.value.name }
    if (isEdit.value && props.category) {
      const res = await adminApi.categories.update(props.category.id, payload)
      emit('saved', res.data)
    } else {
      const res = await adminApi.categories.create(payload)
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
.modal-dialog { background: white; border-radius: 8px; width: 90%; max-width: 480px; box-shadow: 0 8px 32px rgba(0,0,0,0.2); max-height: 90vh; overflow-y: auto; }
.modal-header { display: flex; align-items: center; justify-content: space-between; padding: 1.25rem 1.5rem; border-bottom: 1px solid #e5e5e5; }
.modal-header h3 { margin: 0; font-size: 1.1rem; font-weight: 700; }
.close-btn { background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #666; }
.modal-form { padding: 1.5rem; display: flex; flex-direction: column; gap: 1rem; }
.form-group { display: flex; flex-direction: column; gap: 0.25rem; }
.form-group label { font-size: 0.875rem; font-weight: 600; color: #444; }
.form-group input[type="text"] { padding: 0.5rem 0.75rem; border: 1px solid #ccc; border-radius: 4px; font-size: 0.875rem; }
.lang-grid { display: flex; flex-direction: column; gap: 0.5rem; }
.lang-row { display: flex; align-items: center; gap: 0.75rem; }
.lang-code { font-size: 0.75rem; font-weight: 700; color: #888; width: 2rem; }
.lang-row input { flex: 1; padding: 0.375rem 0.75rem; border: 1px solid #ccc; border-radius: 4px; font-size: 0.875rem; }
.hint { font-size: 0.75rem; color: #888; }
.form-error { color: #dc2626; font-size: 0.875rem; padding: 0.5rem; background: #fef2f2; border-radius: 4px; }
.modal-actions { display: flex; gap: 0.75rem; justify-content: flex-end; margin-top: 0.5rem; }
.btn-primary { padding: 0.5rem 1.25rem; border: none; border-radius: 4px; background: #1a1a1a; color: white; cursor: pointer; font-size: 0.875rem; font-weight: 600; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-secondary { padding: 0.5rem 1.25rem; border: 1px solid #ccc; border-radius: 4px; background: white; cursor: pointer; font-size: 0.875rem; }
</style>
