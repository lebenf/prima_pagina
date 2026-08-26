<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="event-view max-w-3xl mx-auto px-4 py-6">
    <LoadingSpinner v-if="loading" class="mt-16" />

    <div v-else-if="error" class="mt-4 p-3 bg-red-50 text-red-700 text-sm rounded">
      {{ error }}
    </div>

    <template v-else-if="event">
      <header class="event-view__hero">
        <span v-if="event.tags.length" class="category-label">{{ event.tags[0] }}</span>
        <h1 class="event-view__title">{{ event.title }}</h1>
        <p v-if="event.synopsis" class="event-view__synopsis">{{ event.synopsis }}</p>
        <div class="event-view__meta">
          <EventSourceBadge v-if="event.source_count > 1" :count="event.source_count" />
          <span v-if="event.category_name" class="category-name">{{ event.category_name }}</span>
          <RelativeTime :date="event.last_activity_at" />
          <VoteButtons
            target="event"
            :target-id="event.id"
            :initial-vote="event.user_vote ?? 0"
            @vote-changed="onVoteChanged"
          />
          <button
            v-if="auth.isAdmin"
            class="action-btn delete-event-btn"
            @click="confirmingDelete = true"
          >{{ t('events.deleteEvent') }}</button>
        </div>
      </header>

      <ul class="event-member-list">
        <li v-for="article in event.articles" :key="article.id" class="event-member">
          <div class="event-member__main">
            <span v-if="article.feed_title" class="feed-title">{{ article.feed_title }}</span>
            <a
              v-if="article.url"
              :href="article.url"
              target="_blank"
              rel="noopener noreferrer"
              class="member-link"
            >{{ article.title }}</a>
            <span v-else class="member-title">{{ article.title }}</span>
            <RelativeTime :date="article.published_at" />
          </div>
          <div class="event-member__actions">
            <button
              class="action-btn"
              @click="toggleStar(article)"
            >{{ article.is_starred ? '★' : '☆' }}</button>
            <button
              v-if="!article.is_read"
              class="action-btn text-sm"
              @click="markRead(article)"
            >{{ t('article.markRead') }}</button>
            <RouterLink
              :to="{ name: 'reader', query: { article: article.id } }"
              class="action-btn open-reader-btn"
            >{{ t('article.openInReader') }}</RouterLink>
          </div>
        </li>
      </ul>
    </template>

    <ConfirmDialog
      v-if="confirmingDelete"
      :title="t('events.deleteConfirmTitle')"
      :message="t('events.deleteConfirmMessage')"
      @confirm="deleteEvent"
      @cancel="confirmingDelete = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { eventsApi, type EventDetail } from '@/api/events'
import { articlesApi } from '@/api/articles'
import { adminApi } from '@/api/admin'
import { useAuthStore } from '@/stores/auth'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import RelativeTime from '@/components/common/RelativeTime.vue'
import VoteButtons from '@/components/common/VoteButtons.vue'
import EventSourceBadge from '@/components/events/EventSourceBadge.vue'
import ConfirmDialog from '@/components/admin/ConfirmDialog.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const confirmingDelete = ref(false)

const event = ref<EventDetail | null>(null)
const loading = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await eventsApi.get(route.params.id as string)
    event.value = res.data
  } catch {
    error.value = t('common.error')
  } finally {
    loading.value = false
  }
}

function onVoteChanged(vote: number) {
  if (event.value) event.value.user_vote = vote
}

async function markRead(article: { id: string; is_read: boolean }) {
  await articlesApi.updateState(article.id, { is_read: true })
  article.is_read = true
}

async function toggleStar(article: { id: string; is_starred: boolean }) {
  const newState = !article.is_starred
  await articlesApi.updateState(article.id, { is_starred: newState })
  article.is_starred = newState
}

async function deleteEvent() {
  if (!event.value) return
  await adminApi.events.delete(event.value.id)
  router.push({ name: 'events' })
}

onMounted(load)
</script>

<style scoped>
.event-view__hero {
  border-bottom: 2px solid #1f2937;
  padding-bottom: 1rem;
  margin-bottom: 1.5rem;
}
.category-label {
  display: block;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #6b7280;
  margin-bottom: 0.5rem;
}
.event-view__title {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 2rem;
  font-weight: 900;
  line-height: 1.2;
  margin-bottom: 0.75rem;
}
.event-view__synopsis {
  color: #374151;
  font-size: 1rem;
  line-height: 1.6;
  margin-bottom: 0.75rem;
}
.event-view__meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
  color: #9ca3af;
  flex-wrap: wrap;
}
.category-name {
  color: #6b7280;
}
.event-member-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.event-member {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 0;
  border-bottom: 1px solid #e5e7eb;
  flex-wrap: wrap;
}
.event-member__main {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  flex: 1;
}
.feed-title {
  font-weight: 600;
  color: #2563eb;
  font-size: 0.85rem;
}
.member-link, .member-title {
  font-size: 0.95rem;
  color: #111827;
  text-decoration: none;
}
.member-link:hover {
  text-decoration: underline;
}
.event-member__actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.action-btn {
  padding: 0.25rem 0.5rem;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  background: none;
  cursor: pointer;
  font-size: 0.85rem;
  text-decoration: none;
  color: inherit;
}
.action-btn:hover {
  background: #f3f4f6;
}
.open-reader-btn {
  color: #2563eb;
  border-color: #2563eb;
}
.delete-event-btn {
  margin-left: auto;
  color: #dc2626;
  border-color: #dc2626;
}
.delete-event-btn:hover {
  background: #fef2f2;
}
</style>
