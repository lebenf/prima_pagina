<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="admin-section">
    <div class="section-header">
      <h2>{{ t('admin.scheduler.title') }}</h2>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>
    <div v-else class="scheduler-content">
      
      <!-- Current Settings -->
      <div class="settings-card">
        <h3>{{ t('admin.scheduler.currentSettings') }}</h3>
        <div class="settings-grid">
          <div class="setting-item">
            <label>{{ t('admin.scheduler.digestCron') }}</label>
            <div class="setting-value">
              <code>{{ settings?.digest_cron }}</code>
              <span class="setting-desc">({{ settings ? formatCronDescription(settings.digest_cron) : '' }})</span>
            </div>
          </div>
          <div class="setting-item">
            <label>{{ t('admin.scheduler.frontpageCron') }}</label>
            <div class="setting-value">
              <code>{{ settings?.frontpage_cron }}</code>
              <span class="setting-desc">({{ settings ? formatCronDescription(settings.frontpage_cron) : '' }})</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Update Settings Form -->
      <div class="settings-card">
        <h3>{{ t('admin.scheduler.updateSettings') }}</h3>
        <form @submit.prevent="updateSettings" class="settings-form">
          <div class="form-group">
            <label for="digestCron">{{ t('admin.scheduler.digestCron') }}</label>
            <input 
              id="digestCron" 
              v-model="newSettings.digest_cron" 
              type="text" 
              placeholder="0 5 * * *"
              class="form-input"
            />
            <div class="form-hint">{{ t('admin.scheduler.cronFormatHint') }}</div>
          </div>
          
          <div class="form-group">
            <label for="frontpageCron">{{ t('admin.scheduler.frontpageCron') }}</label>
            <input 
              id="frontpageCron" 
              v-model="newSettings.frontpage_cron" 
              type="text" 
              placeholder="0 */2 * * *"
              class="form-input"
            />
            <div class="form-hint">{{ t('admin.scheduler.cronFormatHint') }}</div>
          </div>
          
          <div class="form-actions">
            <button type="submit" class="btn-primary" :disabled="updating">
              {{ updating ? t('common.saving') : t('common.save') }}
            </button>
          </div>
        </form>
      </div>

      <!-- Scheduled Tasks List -->
      <div class="settings-card">
        <h3>{{ t('admin.scheduler.scheduledTasks') }}</h3>
        <div v-if="tasksLoading" class="loading">{{ t('common.loading') }}</div>
        <div v-else class="tasks-list">
          <div v-for="task in tasks" :key="task.id" class="task-item">
            <div class="task-header">
              <strong>{{ task.id }}</strong>
              <span class="task-trigger">{{ task.trigger_type }}</span>
            </div>
            <div class="task-details">
              <div class="task-config">
                <pre>{{ JSON.stringify(task.trigger_config, null, 2) }}</pre>
              </div>
              <div class="task-next-run">
                {{ t('admin.scheduler.nextRun') }}: 
                <span v-if="task.next_run_time">
                  {{ formatDateTime(task.next_run_time) }}
                </span>
                <span v-else class="muted">{{ t('admin.scheduler.never') }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Manual Triggers -->
      <div class="settings-card">
        <h3>{{ t('admin.scheduler.manualTriggers') }}</h3>
        <div class="trigger-actions">
          <button 
            class="btn-secondary" 
            @click="triggerFrontpageCache" 
            :disabled="triggeringFrontpage"
          >
            {{ triggeringFrontpage ? t('common.processing') : t('admin.scheduler.triggerFrontpage') }}
          </button>
          
          <button 
            class="btn-secondary" 
            @click="triggerDigestGeneration" 
            :disabled="triggeringDigest"
          >
            {{ triggeringDigest ? t('common.processing') : t('admin.scheduler.triggerDigest') }}
          </button>
        </div>
        
        <div v-if="triggerResult" class="trigger-result success-msg">
          {{ triggerResult }}
        </div>
        <div v-if="triggerError" class="trigger-result error-msg">
          {{ triggerError }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { adminApi } from '@/api/admin'
import type { ScheduledTaskInfo, TaskScheduleResponse, TaskScheduleUpdate } from '@/api/admin'

const { t } = useI18n()

const loading = ref(true)
const error = ref<string | null>(null)
const settings = ref<TaskScheduleResponse | null>(null)
const newSettings = ref<TaskScheduleUpdate>({})
const updating = ref(false)

const tasksLoading = ref(true)
const tasks = ref<ScheduledTaskInfo[]>([])

const triggeringFrontpage = ref(false)
const triggeringDigest = ref(false)
const triggerResult = ref<string | null>(null)
const triggerError = ref<string | null>(null)

// Fetch current settings
const fetchSettings = async () => {
  try {
    loading.value = true
    error.value = null
    const response = await adminApi.scheduler.getSettings()
    settings.value = response.data
    newSettings.value = {
      digest_cron: response.data.digest_cron,
      frontpage_cron: response.data.frontpage_cron
    }
  } catch (err) {
    error.value = t('admin.scheduler.failedToLoadSettings')
    console.error('Failed to load scheduler settings:', err)
  } finally {
    loading.value = false
  }
}

// Fetch scheduled tasks
const fetchTasks = async () => {
  try {
    tasksLoading.value = true
    const response = await adminApi.scheduler.listTasks()
    tasks.value = response.data.tasks
  } catch (err) {
    console.error('Failed to load scheduled tasks:', err)
  } finally {
    tasksLoading.value = false
  }
}

// Update settings
const updateSettings = async () => {
  try {
    updating.value = true
    error.value = null
    await adminApi.scheduler.updateSettings({
      digest_cron: newSettings.value.digest_cron,
      frontpage_cron: newSettings.value.frontpage_cron
    })
    // Refresh settings
    await fetchSettings()
  } catch (err) {
    error.value = t('admin.scheduler.failedToUpdateSettings')
    console.error('Failed to update scheduler settings:', err)
  } finally {
    updating.value = false
  }
}

// Trigger frontpage cache regeneration
const triggerFrontpageCache = async () => {
  try {
    triggeringFrontpage.value = true
    triggerResult.value = null
    triggerError.value = null
    const response = await adminApi.scheduler.triggerFrontpageCache()
    triggerResult.value = response.data.message
    // Refresh tasks to see new next run times
    await fetchTasks()
  } catch (err) {
    triggerError.value = t('admin.scheduler.failedToTriggerFrontpage')
    console.error('Failed to trigger frontpage cache:', err)
  } finally {
    triggeringFrontpage.value = false
  }
}

// Trigger digest generation
const triggerDigestGeneration = async () => {
  try {
    triggeringDigest.value = true
    triggerResult.value = null
    triggerError.value = null
    const response = await adminApi.scheduler.triggerDigestGeneration()
    triggerResult.value = response.data.message
  } catch (err) {
    triggerError.value = t('admin.scheduler.failedToTriggerDigest')
    console.error('Failed to trigger digest generation:', err)
  } finally {
    triggeringDigest.value = false
  }
}

// Format cron description
const formatCronDescription = (cron: string): string => {
  // Simple cron parser for common patterns
  if (cron === '0 5 * * *') return t('admin.scheduler.dailyAt5AM')
  if (cron === '0 */2 * * *') return t('admin.scheduler.every2Hours')
  if (cron === '0 7 * * *') return t('admin.scheduler.dailyAt7AM')
  if (cron.match(/^0 \*\/\d+ \* \* \*$/)) {
    const match = cron.match(/0 \*\/(\d+) \* \* \*/)
    if (match) {
      const hours = parseInt(match[1])
      return t('admin.scheduler.everyXHours', { hours })
    }
  }
  return t('admin.scheduler.customSchedule')
}

// Format date time
const formatDateTime = (dateString: string): string => {
  const date = new Date(dateString)
  return date.toLocaleString()
}

// Initialize
onMounted(() => {
  fetchSettings()
  fetchTasks()
})
</script>

<style scoped>
.admin-section {
  padding: 1.5rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.section-header h2 {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0;
}

.settings-card {
  background: white;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.settings-card h3 {
  font-size: 1rem;
  font-weight: 600;
  margin: 0 0 1rem;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1rem;
}

.setting-item {
  margin-bottom: 1rem;
}

.setting-item label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: #666;
  margin-bottom: 0.25rem;
}

.setting-value {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.setting-value code {
  background: #f5f5f5;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.875rem;
}

.setting-desc {
  font-size: 0.75rem;
  color: #999;
}

.settings-form {
  max-width: 600px;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  color: #333;
  margin-bottom: 0.25rem;
}

.form-input {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.875rem;
  font-family: monospace;
}

.form-input:focus {
  outline: none;
  border-color: #1a1a1a;
}

.form-hint {
  font-size: 0.75rem;
  color: #999;
  margin-top: 0.25rem;
}

.form-actions {
  margin-top: 1rem;
}

.tasks-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.task-item {
  background: #f9f9f9;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  padding: 1rem;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.task-trigger {
  font-size: 0.75rem;
  color: #666;
  background: white;
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
}

.task-details {
  display: flex;
  gap: 1rem;
}

.task-config {
  flex: 1;
}

.task-config pre {
  margin: 0;
  font-size: 0.75rem;
  background: white;
  padding: 0.5rem;
  border-radius: 4px;
  overflow-x: auto;
}

.task-next-run {
  font-size: 0.875rem;
  color: #666;
  white-space: nowrap;
}

.trigger-actions {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.trigger-result {
  margin-top: 1rem;
  padding: 0.75rem;
  border-radius: 4px;
}

.success-msg {
  background: #d4edda;
  color: #155724;
}

.error-msg {
  background: #f8d7da;
  color: #721c24;
}

.loading {
  color: #666;
  font-style: italic;
}

.muted {
  color: #999;
}
</style>
