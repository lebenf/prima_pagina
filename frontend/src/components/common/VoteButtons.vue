<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="vote-buttons" :class="{ compact }">
    <button
      class="vote-btn vote-up"
      :class="{ active: currentVote === 1 }"
      :aria-label="t('article.voteUp')"
      :title="t('article.voteUp')"
      :disabled="isLoading"
      @click.stop="handleVote(1)"
    >
      👍
      <span v-if="!compact" class="vote-label">{{ t('article.voteUp') }}</span>
    </button>
    <button
      class="vote-btn vote-down"
      :class="{ active: currentVote === -1 }"
      :aria-label="t('article.voteDown')"
      :title="t('article.voteDown')"
      :disabled="isLoading"
      @click.stop="handleVote(-1)"
    >
      👎
      <span v-if="!compact" class="vote-label">{{ t('article.voteDown') }}</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { articlesApi } from '@/api/articles'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  articleId: string
  initialVote?: number
  compact?: boolean
}>()

const emit = defineEmits<{
  'vote-changed': [vote: number, articleId: string]
}>()

const { t } = useI18n()
const currentVote = ref(props.initialVote ?? 0)
const isLoading = ref(false)

async function handleVote(vote: 1 | -1) {
  if (isLoading.value) return

  const newVote = currentVote.value === vote ? 0 : vote
  const previousVote = currentVote.value
  isLoading.value = true
  currentVote.value = newVote

  try {
    if (newVote === 0) {
      await articlesApi.removeVote(props.articleId)
    } else {
      await articlesApi.vote(props.articleId, newVote)
    }
    emit('vote-changed', newVote, props.articleId)
  } catch {
    currentVote.value = previousVote
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.vote-buttons {
  display: flex;
  gap: 0.25rem;
  align-items: center;
}
.vote-btn {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  border: 1px solid transparent;
  border-radius: 4px;
  background: none;
  cursor: pointer;
  font-size: 1rem;
  color: var(--color-text-muted, #6b7280);
  transition: all 0.15s;
  line-height: 1;
}
.vote-btn:hover:not(:disabled) {
  background: var(--color-surface, #f3f4f6);
  border-color: var(--color-border, #e5e7eb);
}
.vote-btn.active.vote-up {
  color: #16a34a;
  background: #f0fdf4;
  border-color: #bbf7d0;
}
.vote-btn.active.vote-down {
  color: #dc2626;
  background: #fef2f2;
  border-color: #fecaca;
}
.vote-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.vote-label {
  font-size: 0.75rem;
}
.compact .vote-btn {
  padding: 0.2rem 0.3rem;
  font-size: 0.85rem;
}
</style>
