<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <Teleport to="body">
    <div class="modal-overlay" @click.self="$emit('close')">
      <div class="modal-panel">
        <header class="modal-header">
          <h3>Script estrazione — {{ feed.title || feed.url }}</h3>
          <button class="close-btn" @click="$emit('close')">×</button>
        </header>

        <div class="modal-body">
          <div v-if="loading" class="modal-loading">{{ t('common.loading') }}</div>
          <div v-else-if="error" class="modal-error">{{ error }}</div>

          <template v-else-if="script">
            <div class="stats-grid">
              <div class="stat">
                <span class="stat-label">Stato</span>
                <span :class="['stat-value', script.is_active ? 'ok' : 'error']">
                  {{ script.is_active ? 'Attivo' : 'Disattivato' }}
                </span>
              </div>
              <div class="stat">
                <span class="stat-label">Successo</span>
                <span class="stat-value">{{ Math.round(script.success_rate * 100) }}%</span>
              </div>
              <div class="stat">
                <span class="stat-label">Fallimenti consec.</span>
                <span :class="['stat-value', script.consecutive_failures > 3 ? 'error' : '']">
                  {{ script.consecutive_failures }}
                </span>
              </div>
              <div class="stat">
                <span class="stat-label">Generato il</span>
                <span class="stat-value">{{ formatDate(script.generated_at) }}</span>
              </div>
            </div>

            <div v-if="script.sample_url" class="sample-url">
              <span class="stat-label">URL campione:</span>
              <a :href="script.sample_url" target="_blank" rel="noopener noreferrer" class="url-link">
                {{ script.sample_url }}
              </a>
            </div>

            <div class="selectors-section">
              <h4>CSS Selectors</h4>
              <table class="selectors-table">
                <tbody>
                  <tr v-for="(selector, field) in script.selectors" :key="field">
                    <td class="selector-field">{{ field }}</td>
                    <td><code class="selector-code">{{ selector }}</code></td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="script-actions">
              <button
                @click="regenerate"
                :disabled="isRegenerating"
                class="btn-secondary"
              >
                {{ isRegenerating ? 'Rigenerazione avviata...' : '🔄 Rigenera script' }}
              </button>
            </div>

            <div v-if="regenerateMessage" class="regenerate-message">
              {{ regenerateMessage }}
            </div>
          </template>

          <div v-else class="no-script">
            <p>Nessuno script generato per questo feed.</p>
            <p>Lo script viene creato automaticamente al primo articolo quando
              <strong>fulltext_mode</strong> è impostato su <code>script</code> o <code>auto</code>.</p>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { adminApi, type AdminFeed, type ExtractionScript } from '@/api/admin'

const props = defineProps<{ feed: AdminFeed }>()
defineEmits<{ close: [] }>()

const { t } = useI18n()
const script = ref<ExtractionScript | null>(props.feed.extraction_script)
const loading = ref(false)
const error = ref<string | null>(null)
const isRegenerating = ref(false)
const regenerateMessage = ref<string | null>(null)

onMounted(async () => {
  if (script.value) return
  loading.value = true
  try {
    const res = await adminApi.extractionScript.get(props.feed.id)
    script.value = res.data
  } catch (e: any) {
    if (e.response?.status === 404) {
      script.value = null
    } else {
      error.value = t('common.error')
    }
  } finally {
    loading.value = false
  }
})

async function regenerate() {
  isRegenerating.value = true
  regenerateMessage.value = null
  try {
    await adminApi.extractionScript.regenerate(props.feed.id)
    regenerateMessage.value = 'Rigenerazione avviata in background. Aggiorna tra qualche minuto.'
  } catch {
    regenerateMessage.value = 'Errore durante la rigenerazione. Riprova.'
  } finally {
    isRegenerating.value = false
  }
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString()
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
  padding: 1rem;
}

.modal-panel {
  background: white;
  border-radius: 8px;
  width: 100%;
  max-width: 560px;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #e5e5e5;
}

.modal-header h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 700;
  color: #111827;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #6b7280;
  line-height: 1;
  padding: 0;
}

.modal-body {
  padding: 1.25rem;
}

.modal-loading, .modal-error {
  text-align: center;
  color: #6b7280;
  padding: 1rem;
}

.modal-error { color: #dc2626; }

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.stat {
  background: #f9fafb;
  border-radius: 4px;
  padding: 0.625rem 0.75rem;
}

.stat-label {
  display: block;
  font-size: 0.75rem;
  color: #6b7280;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.stat-value {
  display: block;
  font-size: 0.9rem;
  font-weight: 700;
  margin-top: 0.2rem;
  color: #111827;
}

.stat-value.ok { color: #059669; }
.stat-value.error { color: #dc2626; }

.sample-url {
  margin-bottom: 1rem;
  font-size: 0.8rem;
  word-break: break-all;
}

.url-link {
  color: #2563eb;
  text-decoration: underline;
}

.selectors-section h4 {
  font-size: 0.875rem;
  font-weight: 700;
  margin: 0 0 0.5rem;
  color: #374151;
}

.selectors-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
}

.selectors-table tr:nth-child(even) { background: #f9fafb; }

.selector-field {
  padding: 0.375rem 0.5rem;
  color: #6b7280;
  font-weight: 600;
  white-space: nowrap;
  width: 100px;
}

.selector-code {
  font-family: monospace;
  font-size: 0.8rem;
  color: #1f2937;
  padding: 0 0.25rem;
}

.script-actions {
  margin-top: 1rem;
  display: flex;
  gap: 0.75rem;
}

.btn-secondary {
  padding: 0.5rem 1rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  font-size: 0.875rem;
}

.btn-secondary:hover:not(:disabled) { background: #f3f4f6; }
.btn-secondary:disabled { opacity: 0.6; cursor: not-allowed; }

.regenerate-message {
  margin-top: 0.75rem;
  font-size: 0.8rem;
  color: #059669;
  background: #f0fdf4;
  border-radius: 4px;
  padding: 0.5rem 0.75rem;
}

.no-script {
  font-size: 0.875rem;
  color: #6b7280;
  line-height: 1.6;
}

.no-script code {
  background: #f3f4f6;
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
  font-size: 0.8rem;
}
</style>
