<template>
  <div class="admin-section">
    <div class="section-header">
      <h2>{{ t('admin.feeds.title') }}</h2>
      <button class="btn-primary" @click="openCreate">+ {{ t('admin.feeds.addFeed') }}</button>
    </div>

    <div class="filter-bar">
      <select v-model="filterCat">
        <option value="">Tutte le categorie</option>
        <option v-for="cat in categories" :key="cat.id" :value="cat.id">
          {{ cat.name?.it || cat.slug }}
        </option>
      </select>
      <input v-model="search" type="search" :placeholder="t('common.search')" class="search-input" />
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>
    <div v-else>
      <table class="admin-table">
        <thead>
          <tr>
            <th>Titolo</th>
            <th>Categoria</th>
            <th>{{ t('admin.feeds.interval') }}</th>
            <th>Status</th>
            <th>Azioni</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="feed in filteredFeeds"
            :key="feed.id"
            :class="{
              'row-disabled': !feed.is_active,
              'row-error': feed.error_count > 5 && feed.is_active,
            }"
          >
            <td>
              <span class="feed-title">{{ feed.title || feed.url }}</span>
              <span v-if="!feed.is_active" class="badge badge-disabled">Disattivato</span>
              <span v-else-if="feed.error_count > 5" class="badge badge-error">
                {{ t('admin.feeds.errorCount', { count: feed.error_count }) }}
              </span>
            </td>
            <td>{{ feed.category_name || '—' }}</td>
            <td>{{ feed.fetch_interval_min }} min</td>
            <td>
              <span :class="['status-dot', statusClass(feed)]">
                {{ feed.last_http_status || t('admin.feeds.neverFetched') }}
              </span>
            </td>
            <td class="actions">
              <button class="btn-icon" @click="openEdit(feed)" title="Modifica">✏️</button>
              <button class="btn-icon" @click="refresh(feed)" :disabled="refreshing === feed.id" title="Refresh">🔄</button>
              <button class="btn-icon" @click="confirmDelete(feed)" title="Elimina">🗑️</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <FeedFormModal
      v-if="showModal"
      :feed="editingFeed"
      :categories="categories"
      @close="showModal = false"
      @saved="onSaved"
    />

    <ConfirmDialog
      v-if="showConfirm"
      :title="t('common.delete')"
      :message="t('admin.feeds.deleteConfirm', { title: deletingFeed?.title || deletingFeed?.url })"
      @confirm="doDelete"
      @cancel="showConfirm = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { adminApi, type AdminFeed, type AdminCategory } from '@/api/admin'
import FeedFormModal from './FeedFormModal.vue'
import ConfirmDialog from './ConfirmDialog.vue'

const { t } = useI18n()

const feeds = ref<AdminFeed[]>([])
const categories = ref<AdminCategory[]>([])
const loading = ref(false)
const error = ref('')
const search = ref('')
const filterCat = ref('')
const showModal = ref(false)
const editingFeed = ref<AdminFeed | null>(null)
const showConfirm = ref(false)
const deletingFeed = ref<AdminFeed | null>(null)
const refreshing = ref<string | null>(null)

const filteredFeeds = computed(() => {
  let list = feeds.value
  if (filterCat.value) list = list.filter(f => f.category_id === filterCat.value)
  if (search.value) {
    const q = search.value.toLowerCase()
    list = list.filter(f => f.title?.toLowerCase().includes(q) || f.url.toLowerCase().includes(q))
  }
  return list
})

function statusClass(feed: AdminFeed) {
  if (!feed.last_http_status) return 'status-grey'
  if (feed.last_http_status < 300) return 'status-green'
  if (feed.last_http_status < 400) return 'status-orange'
  return 'status-red'
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [feedsRes, catsRes] = await Promise.all([
      adminApi.feeds.list(),
      adminApi.categories.list(),
    ])
    feeds.value = feedsRes.data
    categories.value = catsRes.data
  } catch {
    error.value = t('common.error')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingFeed.value = null
  showModal.value = true
}

function openEdit(feed: AdminFeed) {
  editingFeed.value = feed
  showModal.value = true
}

async function refresh(feed: AdminFeed) {
  refreshing.value = feed.id
  try {
    await adminApi.feeds.refresh(feed.id)
  } catch {
    error.value = t('common.error')
  } finally {
    refreshing.value = null
  }
}

function confirmDelete(feed: AdminFeed) {
  deletingFeed.value = feed
  showConfirm.value = true
}

async function doDelete() {
  if (!deletingFeed.value) return
  try {
    await adminApi.feeds.delete(deletingFeed.value.id)
    feeds.value = feeds.value.filter(f => f.id !== deletingFeed.value!.id)
  } catch {
    error.value = t('common.error')
  } finally {
    showConfirm.value = false
    deletingFeed.value = null
  }
}

function onSaved(feed: AdminFeed) {
  const idx = feeds.value.findIndex(f => f.id === feed.id)
  if (idx >= 0) {
    feeds.value[idx] = feed
  } else {
    feeds.value.push(feed)
  }
  showModal.value = false
}

onMounted(load)
</script>

<style scoped>
.admin-section { padding: 1.5rem; }
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.25rem; }
.section-header h2 { font-size: 1.25rem; font-weight: 700; margin: 0; }
.filter-bar { display: flex; gap: 0.75rem; margin-bottom: 1rem; }
.filter-bar select, .search-input {
  padding: 0.375rem 0.75rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.875rem;
}
.search-input { flex: 1; max-width: 300px; }
.admin-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.admin-table th {
  text-align: left;
  padding: 0.75rem 1rem;
  border-bottom: 2px solid #e5e5e5;
  font-weight: 600;
  color: #555;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.admin-table td { padding: 0.75rem 1rem; border-bottom: 1px solid #f0f0f0; vertical-align: middle; }
.row-disabled { opacity: 0.5; }
.row-error { background: #fffbeb; }
.feed-title { font-weight: 500; }
.badge {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  margin-left: 0.5rem;
}
.badge-disabled { background: #f3f4f6; color: #6b7280; }
.badge-error { background: #fef3c7; color: #92400e; }
.status-dot { font-size: 0.875rem; font-weight: 600; }
.status-green { color: #059669; }
.status-orange { color: #d97706; }
.status-red { color: #dc2626; }
.status-grey { color: #9ca3af; }
.actions { display: flex; gap: 0.25rem; }
.btn-icon { background: none; border: none; cursor: pointer; font-size: 1rem; padding: 0.25rem; border-radius: 4px; opacity: 0.7; }
.btn-icon:hover:not(:disabled) { opacity: 1; background: #f0f0f0; }
.btn-icon:disabled { opacity: 0.3; cursor: not-allowed; }
.btn-primary { padding: 0.5rem 1rem; border: none; border-radius: 4px; background: #1a1a1a; color: white; cursor: pointer; font-size: 0.875rem; font-weight: 600; }
.loading, .error-msg { padding: 2rem; text-align: center; color: #888; }
.error-msg { color: #dc2626; }
</style>
