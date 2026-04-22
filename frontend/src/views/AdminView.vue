<template>
  <div class="admin-container">
    <header class="admin-header">
      <h1>{{ t('admin.title') }}</h1>
      <span class="admin-badge">Admin</span>
    </header>

    <nav class="admin-tabs" role="tablist">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        role="tab"
        :aria-selected="activeTab === tab.id"
        :class="['tab-btn', { active: activeTab === tab.id }]"
        @click="activeTab = tab.id"
      >
        <span class="tab-icon">{{ tab.icon }}</span>
        {{ t(tab.labelKey) }}
      </button>
    </nav>

    <div class="admin-content" role="tabpanel">
      <AdminUsers v-if="activeTab === 'users'" />
      <AdminSessions v-else-if="activeTab === 'sessions'" />
      <AdminFeeds v-else-if="activeTab === 'feeds'" />
      <AdminCategories v-else-if="activeTab === 'categories'" />
      <AdminLLMConfigs v-else-if="activeTab === 'llm'" />
      <AdminPlugins v-else-if="activeTab === 'plugins'" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AdminUsers from '@/components/admin/AdminUsers.vue'
import AdminSessions from '@/components/admin/AdminSessions.vue'
import AdminFeeds from '@/components/admin/AdminFeeds.vue'
import AdminCategories from '@/components/admin/AdminCategories.vue'
import AdminLLMConfigs from '@/components/admin/AdminLLMConfigs.vue'
import AdminPlugins from '@/components/admin/AdminPlugins.vue'

const { t } = useI18n()
const auth = useAuthStore()
const router = useRouter()

// Double-check: redirect non-admin users
if (!auth.isAdmin) {
  router.replace('/')
}

const tabs = [
  { id: 'users',      icon: '👤', labelKey: 'admin.tabs.users' },
  { id: 'sessions',   icon: '🔐', labelKey: 'admin.tabs.sessions' },
  { id: 'feeds',      icon: '📡', labelKey: 'admin.tabs.feeds' },
  { id: 'categories', icon: '🏷️', labelKey: 'admin.tabs.categories' },
  { id: 'llm',        icon: '🤖', labelKey: 'admin.tabs.llm' },
  { id: 'plugins',    icon: '🔔', labelKey: 'admin.tabs.plugins' },
]

const activeTab = ref('users')
</script>

<style scoped>
.admin-container {
  max-width: 1200px;
  margin: 0 auto;
}

.admin-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem 1.5rem 0;
  border-bottom: 2px solid #1a1a1a;
  padding-bottom: 1rem;
}

.admin-header h1 {
  font-size: 1.5rem;
  font-weight: 900;
  letter-spacing: -0.02em;
  margin: 0;
}

.admin-badge {
  background: #1a1a1a;
  color: white;
  padding: 0.125rem 0.625rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.admin-tabs {
  display: flex;
  gap: 0;
  padding: 0 1.5rem;
  border-bottom: 1px solid #e5e5e5;
  overflow-x: auto;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.875rem 1.25rem;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  color: #666;
  white-space: nowrap;
  margin-bottom: -1px;
  transition: color 0.15s, border-color 0.15s;
}

.tab-btn:hover {
  color: #1a1a1a;
}

.tab-btn.active {
  color: #1a1a1a;
  border-bottom-color: #1a1a1a;
  font-weight: 700;
}

.tab-icon {
  font-size: 1rem;
}

.admin-content {
  background: white;
}
</style>
