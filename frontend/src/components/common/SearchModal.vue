<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <Teleport to="body">
    <Transition name="modal-fade">
      <div v-if="store.isOpen" class="search-overlay" @click.self="store.close()">
        <div class="search-modal" role="dialog" :aria-label="t('search.openSearch')">

          <div class="search-input-wrapper">
            <svg class="search-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              ref="inputRef"
              v-model="localQuery"
              :placeholder="t('search.placeholder')"
              class="search-input"
              type="search"
              autocomplete="off"
              @input="store.debouncedSearch(localQuery)"
              @keydown.escape="store.close()"
              @keydown.down.prevent="moveSelection(1)"
              @keydown.up.prevent="moveSelection(-1)"
              @keydown.enter.prevent="openSelected"
            />
            <kbd class="search-esc">Esc</kbd>
          </div>

          <div v-if="store.isLoading" class="search-loading">
            <LoadingSpinner size="sm" />
          </div>

          <div v-else-if="store.results.length > 0" class="search-results">
            <div class="search-count">
              {{ t('search.resultCount', { count: store.total }) }}
            </div>
            <ul class="result-list" role="listbox">
              <li
                v-for="(result, index) in store.results"
                :key="result.id"
                :class="['result-item', { selected: selectedIndex === index }]"
                role="option"
                :aria-selected="selectedIndex === index"
                @click="openArticle(result)"
                @mouseenter="selectedIndex = index"
              >
                <div class="result-source">{{ result.feed_title }}</div>
                <!-- HTML sanitizzato: solo <mark> dal backend -->
                <div
                  class="result-title"
                  v-html="result.title_highlighted || result.title"
                />
                <div
                  v-if="result.excerpt_snippet"
                  class="result-excerpt"
                  v-html="result.excerpt_snippet"
                />
                <div class="result-meta">
                  <RelativeTime v-if="result.published_at" :date="result.published_at" />
                  <span v-if="result.is_read" class="read-badge">
                    {{ t('article.markRead') }}
                  </span>
                </div>
              </li>
            </ul>

            <div v-if="store.total > 20" class="search-pagination">
              <button :disabled="store.page <= 1" @click="changePage(store.page - 1)">
                ← {{ t('common.prev') }}
              </button>
              <span>{{ store.page }} / {{ Math.ceil(store.total / 20) }}</span>
              <button
                :disabled="store.page >= Math.ceil(store.total / 20)"
                @click="changePage(store.page + 1)"
              >
                {{ t('common.next') }} →
              </button>
            </div>
          </div>

          <div v-else-if="localQuery.length >= 2 && !store.isLoading" class="search-empty">
            {{ t('search.noResults', { query: localQuery }) }}
          </div>

          <div v-else class="search-hint">
            {{ t('search.hint') }}
          </div>

        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useSearchStore } from '@/stores/search'
import { useI18n } from 'vue-i18n'
import type { SearchResult } from '@/api/search'
import RelativeTime from './RelativeTime.vue'
import LoadingSpinner from './LoadingSpinner.vue'

const store = useSearchStore()
const router = useRouter()
const { t } = useI18n()
const inputRef = ref<HTMLInputElement | null>(null)
const localQuery = ref('')
const selectedIndex = ref(0)

watch(
  () => store.isOpen,
  async (open) => {
    if (open) {
      localQuery.value = ''
      selectedIndex.value = 0
      await nextTick()
      inputRef.value?.focus()
    }
  },
)

watch(
  () => store.results,
  () => { selectedIndex.value = 0 },
)

function moveSelection(delta: number) {
  const max = store.results.length - 1
  selectedIndex.value = Math.max(0, Math.min(max, selectedIndex.value + delta))
}

function openSelected() {
  const result = store.results[selectedIndex.value]
  if (result) openArticle(result)
}

function openArticle(result: SearchResult) {
  store.close()
  router.push({ name: 'reader', query: { article: result.id } })
}

async function changePage(p: number) {
  await store.search(store.query, p)
}
</script>

<style scoped>
.search-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 10vh;
}

.search-modal {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  width: 100%;
  max-width: 640px;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.search-input-wrapper {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.search-icon {
  width: 1.25rem;
  height: 1.25rem;
  color: #9ca3af;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 1rem;
  color: #111827;
  background: transparent;
}

.search-input::placeholder {
  color: #9ca3af;
}

/* Remove browser search clear button */
.search-input::-webkit-search-cancel-button {
  display: none;
}

.search-esc {
  font-size: 0.7rem;
  color: #6b7280;
  background: #f3f4f6;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  padding: 0.1rem 0.4rem;
  flex-shrink: 0;
}

.search-loading {
  display: flex;
  justify-content: center;
  padding: 2rem;
}

.search-results {
  overflow-y: auto;
  flex: 1;
}

.search-count {
  font-size: 0.75rem;
  color: #6b7280;
  padding: 0.5rem 1.25rem;
  border-bottom: 1px solid #f3f4f6;
}

.result-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.result-item {
  padding: 0.75rem 1.25rem;
  cursor: pointer;
  border-bottom: 1px solid #f9fafb;
  transition: background 0.1s;
}

.result-item:hover,
.result-item.selected {
  background: #f3f4f6;
}

.result-source {
  font-size: 0.7rem;
  color: #2563eb;
  font-weight: 600;
  margin-bottom: 0.2rem;
}

.result-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #111827;
  line-height: 1.3;
  margin-bottom: 0.25rem;
}

.result-excerpt {
  font-size: 0.8rem;
  color: #6b7280;
  line-height: 1.4;
  margin-bottom: 0.25rem;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.result-meta {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  font-size: 0.7rem;
  color: #9ca3af;
}

.read-badge {
  background: #f0fdf4;
  color: #16a34a;
  padding: 0.1rem 0.4rem;
  border-radius: 3px;
  font-weight: 600;
}

.search-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 0.75rem 1.25rem;
  border-top: 1px solid #e5e7eb;
  font-size: 0.8rem;
  color: #374151;
}

.search-pagination button {
  padding: 0.25rem 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  font-size: 0.8rem;
}

.search-pagination button:hover:not(:disabled) {
  background: #f3f4f6;
}

.search-pagination button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.search-empty,
.search-hint {
  padding: 2rem 1.25rem;
  text-align: center;
  font-size: 0.875rem;
  color: #6b7280;
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.15s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
</style>
