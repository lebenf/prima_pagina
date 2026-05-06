<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <Teleport to="body">
    <div class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-dialog" role="dialog" aria-modal="true">
        <div class="modal-header">
          <h3>{{ isEdit ? t('admin.feeds.editFeed') : t('admin.feeds.addFeed') }}</h3>
          <button class="close-btn" @click="$emit('close')">×</button>
        </div>

        <form @submit.prevent="submit" class="modal-form">
          <div class="form-group">
            <label>URL feed *</label>
            <div class="input-with-spinner">
              <input
                v-model="form.url"
                type="url"
                required
                placeholder="https://example.com/feed.xml"
                @blur="discover"
              />
              <span v-if="discovering" class="spinner">⏳</span>
            </div>
            <small v-if="discovering" class="hint">{{ t('admin.feeds.discovering') }}</small>
          </div>

          <div class="form-group">
            <label>Titolo</label>
            <input v-model="form.title" type="text" placeholder="Titolo del feed" />
          </div>

          <div class="form-group">
            <label>Categoria</label>
            <select v-model="form.category_id">
              <option value="">Nessuna</option>
              <option v-for="cat in categories" :key="cat.id" :value="cat.id">
                {{ cat.name?.it || cat.slug }}
              </option>
            </select>
          </div>

          <div class="form-group">
            <label>{{ t('admin.feeds.interval') }}: {{ form.fetch_interval_min }} min</label>
            <input v-model.number="form.fetch_interval_min" type="range" min="5" max="1440" step="5" />
          </div>

          <div class="form-group">
            <label>{{ t('admin.feeds.weight') }}: {{ form.source_weight.toFixed(1) }}</label>
            <input v-model.number="form.source_weight" type="range" min="0.1" max="5.0" step="0.1" />
          </div>

          <div class="form-group form-group-inline">
            <label>{{ t('admin.users.active') }}</label>
            <input v-model="form.is_active" type="checkbox" />
          </div>

          <div class="form-group form-group-inline">
            <label>{{ t('admin.feeds.fulltextEnabled') }}</label>
            <input v-model="form.fulltext_enabled" type="checkbox" />
          </div>

          <template v-if="form.fulltext_enabled">
            <div class="form-group">
              <label>{{ t('admin.feeds.fulltextMode') }}</label>
              <select v-model="form.fulltext_mode">
                <option value="trafilatura">trafilatura</option>
                <option value="auto">auto</option>
                <option value="script">script</option>
              </select>
            </div>

            <div class="form-group form-group-inline">
              <label>{{ t('admin.feeds.fulltextIncludeImages') }}</label>
              <input v-model="form.fulltext_include_images" type="checkbox" />
            </div>
          </template>

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
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { computed } from 'vue'
import { adminApi, type AdminFeed, type AdminCategory } from '@/api/admin'

const props = defineProps<{
  feed?: AdminFeed | null
  categories: AdminCategory[]
}>()

const emit = defineEmits<{
  close: []
  saved: [feed: AdminFeed]
}>()

const { t } = useI18n()
const isEdit = computed(() => !!props.feed)

const defaultForm = () => ({
  url: '',
  title: '',
  category_id: '',
  fetch_interval_min: 60,
  source_weight: 1.0,
  is_active: true,
  fulltext_enabled: false,
  fulltext_mode: 'trafilatura',
  fulltext_include_images: false,
})

const form = ref(defaultForm())
const saving = ref(false)
const discovering = ref(false)
const error = ref('')

watch(() => props.feed, (f) => {
  if (f) {
    form.value = {
      url: f.url,
      title: f.title ?? '',
      category_id: f.category_id || '',
      fetch_interval_min: f.fetch_interval_min,
      source_weight: f.source_weight,
      is_active: f.is_active,
      fulltext_enabled: f.fulltext_enabled,
      fulltext_mode: f.fulltext_mode || 'trafilatura',
      fulltext_include_images: f.fulltext_include_images,
    }
  } else {
    form.value = defaultForm()
  }
}, { immediate: true })

async function discover() {
  if (!form.value.url || isEdit.value || form.value.title) return
  discovering.value = true
  try {
    const res = await adminApi.feeds.discover(form.value.url)
    if (res.data.title && !form.value.title) {
      form.value.title = res.data.title
    }
  } catch {
    // silent — user can fill title manually
  } finally {
    discovering.value = false
  }
}

async function submit() {
  error.value = ''
  saving.value = true
  try {
    const payload = {
      url: form.value.url,
      title: form.value.title || undefined,
      category_id: form.value.category_id || undefined,
      fetch_interval_min: form.value.fetch_interval_min,
      source_weight: form.value.source_weight,
      is_active: form.value.is_active,
      fulltext_enabled: form.value.fulltext_enabled,
      fulltext_mode: form.value.fulltext_mode,
      fulltext_include_images: form.value.fulltext_include_images,
    }
    if (isEdit.value && props.feed) {
      const res = await adminApi.feeds.update(props.feed.id, payload)
      emit('saved', res.data)
    } else {
      const res = await adminApi.feeds.create(payload)
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
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 900;
}
.modal-dialog {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 520px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  max-height: 90vh;
  overflow-y: auto;
}
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid #e5e5e5;
}
.modal-header h3 { margin: 0; font-size: 1.1rem; font-weight: 700; }
.close-btn { background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #666; }
.modal-form { padding: 1.5rem; display: flex; flex-direction: column; gap: 1rem; }
.form-group { display: flex; flex-direction: column; gap: 0.25rem; }
.form-group label { font-size: 0.875rem; font-weight: 600; color: #444; }
.form-group input[type="url"], .form-group input[type="text"], .form-group select {
  padding: 0.5rem 0.75rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.875rem;
}
.form-group-inline { flex-direction: row; align-items: center; gap: 0.5rem; }
.input-with-spinner { display: flex; gap: 0.5rem; align-items: center; }
.input-with-spinner input { flex: 1; }
.hint { font-size: 0.75rem; color: #888; }
.form-error { color: #dc2626; font-size: 0.875rem; padding: 0.5rem; background: #fef2f2; border-radius: 4px; }
.modal-actions { display: flex; gap: 0.75rem; justify-content: flex-end; margin-top: 0.5rem; }
.btn-primary {
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
.btn-secondary {
  padding: 0.5rem 1.25rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  font-size: 0.875rem;
}
</style>
