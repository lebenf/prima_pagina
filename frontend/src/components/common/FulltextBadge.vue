<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <span class="fulltext-badge-wrap">
    <span
      class="fulltext-ok"
      :title="t('article.fulltextFetchedAt', { date: fetchedAtFormatted })"
    >✦</span>
    <span class="report-wrap" ref="wrapRef">
      <button
        class="report-btn"
        :title="t('article.fulltextReport')"
        @click.stop="toggle"
      >⚑</button>
      <div v-if="open" class="report-popover" @click.stop>
        <template v-if="sent">
          <span class="sent-msg">{{ t('article.fulltextReportSent') }} ✓</span>
        </template>
        <template v-else>
          <textarea
            v-model="message"
            class="report-textarea"
            :placeholder="t('article.fulltextReportPlaceholder')"
            rows="3"
            @keydown.escape="open = false"
          />
          <div class="report-actions">
            <button class="btn-cancel" @click="open = false">✕</button>
            <button class="btn-submit" :disabled="loading" @click="submit">
              {{ loading ? '…' : '↑' }}
            </button>
          </div>
        </template>
      </div>
    </span>
  </span>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { articlesApi } from '@/api/articles'

const props = defineProps<{
  articleId: string
  fetchedAt: string
}>()

const emit = defineEmits<{ reported: [] }>()

const { t, locale } = useI18n()

const open = ref(false)
const message = ref('')
const loading = ref(false)
const sent = ref(false)
const wrapRef = ref<HTMLElement | null>(null)

const fetchedAtFormatted = computed(() =>
  new Intl.DateTimeFormat(locale.value, { dateStyle: 'long', timeStyle: 'short' }).format(new Date(props.fetchedAt))
)

function toggle() {
  if (sent.value) { open.value = false; sent.value = false; message.value = ''; return }
  open.value = !open.value
}

async function submit() {
  loading.value = true
  try {
    await articlesApi.reportFulltext(props.articleId, message.value.trim() || undefined)
    sent.value = true
    emit('reported')
    setTimeout(() => { open.value = false; sent.value = false; message.value = '' }, 2000)
  } catch { /* ignore */ } finally {
    loading.value = false
  }
}

function onDocClick(e: MouseEvent) {
  if (open.value && wrapRef.value && !wrapRef.value.contains(e.target as Node)) {
    open.value = false
  }
}

onMounted(() => document.addEventListener('click', onDocClick))
onUnmounted(() => document.removeEventListener('click', onDocClick))
</script>

<style scoped>
.fulltext-badge-wrap {
  display: inline-flex;
  align-items: center;
  gap: 0.15rem;
}
.fulltext-ok {
  font-size: 0.65rem;
  color: var(--bbf-ok);
  cursor: default;
}
.report-wrap {
  position: relative;
  display: inline-flex;
}
.report-btn {
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  font-size: 0.6rem;
  color: var(--bbf-ink-4);
  line-height: 1;
  opacity: 0.5;
  transition: opacity 0.15s, color 0.15s;
}
.report-btn:hover {
  color: var(--bbf-warn);
  opacity: 1;
}
.report-popover {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  z-index: 100;
  background: var(--bbf-surface);
  border: 1px solid var(--bbf-line);
  border-radius: var(--bbf-r-md);
  box-shadow: var(--bbf-shadow-3);
  padding: 0.5rem;
  width: 220px;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.report-textarea {
  width: 100%;
  font-size: 0.8rem;
  border: 1px solid var(--bbf-line-strong);
  border-radius: var(--bbf-r-sm);
  padding: 0.3rem 0.4rem;
  resize: none;
  font-family: var(--bbf-font);
  line-height: 1.4;
  box-sizing: border-box;
  background: var(--bbf-surface-2);
  color: var(--bbf-ink);
}
.report-textarea:focus {
  outline: none;
  border-color: var(--bbf-primary);
}
.report-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.3rem;
}
.btn-cancel, .btn-submit {
  padding: 0.15rem 0.5rem;
  border-radius: var(--bbf-r-sm);
  border: 1px solid var(--bbf-line-strong);
  background: none;
  cursor: pointer;
  font-size: 0.8rem;
  color: var(--bbf-ink-2);
}
.btn-submit {
  background: var(--bbf-primary);
  color: white;
  border-color: var(--bbf-primary);
}
.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.sent-msg {
  font-size: 0.8rem;
  color: var(--bbf-ok);
  padding: 0.25rem 0;
  text-align: center;
}
</style>
