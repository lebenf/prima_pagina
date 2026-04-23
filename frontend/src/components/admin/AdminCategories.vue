<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="admin-section">
    <div class="section-header">
      <h2>{{ t('admin.categories.title') }}</h2>
      <button class="btn-primary" @click="openCreate">+ {{ t('admin.categories.addCategory') }}</button>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>
    <div v-else>
      <table class="admin-table">
        <thead>
          <tr>
            <th>{{ t('admin.categories.slug') }}</th>
            <th>IT</th>
            <th>EN</th>
            <th>DE</th>
            <th>Feed</th>
            <th>Azioni</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="cat in categories" :key="cat.id">
            <td><code>{{ cat.slug }}</code></td>
            <td>{{ cat.name?.it || '—' }}</td>
            <td>{{ cat.name?.en || '—' }}</td>
            <td>{{ cat.name?.de || '—' }}</td>
            <td>{{ cat.feed_count ?? '—' }}</td>
            <td class="actions">
              <button class="btn-icon" @click="openEdit(cat)">✏️</button>
              <button class="btn-icon" @click="confirmDelete(cat)">🗑️</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <CategoryFormModal
      v-if="showModal"
      :category="editingCat"
      @close="showModal = false"
      @saved="onSaved"
    />

    <ConfirmDialog
      v-if="showConfirm"
      :title="t('common.delete')"
      :message="t('admin.categories.deleteConfirm', { slug: deletingCat?.slug })"
      @confirm="doDelete"
      @cancel="showConfirm = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { adminApi, type AdminCategory } from '@/api/admin'
import CategoryFormModal from './CategoryFormModal.vue'
import ConfirmDialog from './ConfirmDialog.vue'

const { t } = useI18n()

const categories = ref<AdminCategory[]>([])
const loading = ref(false)
const error = ref('')
const showModal = ref(false)
const editingCat = ref<AdminCategory | null>(null)
const showConfirm = ref(false)
const deletingCat = ref<AdminCategory | null>(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await adminApi.categories.list()
    categories.value = res.data
  } catch {
    error.value = t('common.error')
  } finally {
    loading.value = false
  }
}

function openCreate() { editingCat.value = null; showModal.value = true }
function openEdit(cat: AdminCategory) { editingCat.value = cat; showModal.value = true }
function confirmDelete(cat: AdminCategory) { deletingCat.value = cat; showConfirm.value = true }

async function doDelete() {
  if (!deletingCat.value) return
  try {
    await adminApi.categories.delete(deletingCat.value.id)
    categories.value = categories.value.filter(c => c.id !== deletingCat.value!.id)
  } catch {
    error.value = t('common.error')
  } finally {
    showConfirm.value = false
    deletingCat.value = null
  }
}

function onSaved(cat: AdminCategory) {
  const idx = categories.value.findIndex(c => c.id === cat.id)
  if (idx >= 0) { categories.value[idx] = cat } else { categories.value.push(cat) }
  showModal.value = false
}

onMounted(load)
</script>

<style scoped>
.admin-section { padding: 1.5rem; }
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.25rem; }
.section-header h2 { font-size: 1.25rem; font-weight: 700; margin: 0; }
.admin-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.admin-table th { text-align: left; padding: 0.75rem 1rem; border-bottom: 2px solid #e5e5e5; font-weight: 600; color: #555; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }
.admin-table td { padding: 0.75rem 1rem; border-bottom: 1px solid #f0f0f0; vertical-align: middle; }
code { background: #f3f4f6; padding: 0.125rem 0.375rem; border-radius: 3px; font-size: 0.875rem; }
.actions { display: flex; gap: 0.25rem; }
.btn-icon { background: none; border: none; cursor: pointer; font-size: 1rem; padding: 0.25rem; border-radius: 4px; opacity: 0.7; }
.btn-icon:hover { opacity: 1; background: #f0f0f0; }
.btn-primary { padding: 0.5rem 1rem; border: none; border-radius: 4px; background: #1a1a1a; color: white; cursor: pointer; font-size: 0.875rem; font-weight: 600; }
.loading, .error-msg { padding: 2rem; text-align: center; color: #888; }
.error-msg { color: #dc2626; }
</style>
