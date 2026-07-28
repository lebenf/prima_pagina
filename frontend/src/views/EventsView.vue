<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="events-view max-w-3xl mx-auto px-4 py-6">
    <h1 class="events-view__title">{{ t('events.title') }}</h1>

    <template v-if="eventsStore.isLoading && eventsStore.events.length === 0">
      <div class="flex items-center justify-center py-12">
        <div class="w-6 h-6 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
      </div>
    </template>

    <template v-else-if="eventsStore.events.length === 0">
      <p class="px-4 py-8 text-center text-sm text-gray-400">{{ t('events.noEvents') }}</p>
    </template>

    <template v-else>
      <ul class="events-view__list">
        <li v-for="event in eventsStore.events" :key="event.id">
          <EventCard
            size="row"
            :event="event"
            @click="router.push({ name: 'event', params: { id: event.id } })"
            @vote-changed="onVoteChanged"
          />
        </li>
      </ul>

      <InfiniteScroll
        :loading="eventsStore.isLoading"
        :has-more="eventsStore.pagination.page < eventsStore.pagination.pages"
        @load-more="eventsStore.loadNextPage()"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useEventsStore } from '@/stores/events'
import EventCard from '@/components/frontpage/EventCard.vue'
import InfiniteScroll from '@/components/common/InfiniteScroll.vue'

const { t } = useI18n()
const router = useRouter()
const eventsStore = useEventsStore()

function onVoteChanged(vote: number, eventId: string) {
  const event = eventsStore.events.find(e => e.id === eventId)
  if (event) event.user_vote = vote
}

onMounted(() => eventsStore.load())
</script>

<style scoped>
.events-view__title {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 1.75rem;
  font-weight: 900;
  margin-bottom: 1.25rem;
}
.events-view__list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}
.events-view__list li {
  padding-bottom: 1.25rem;
  border-bottom: 1px solid #e5e7eb;
}
.events-view__list li:last-child {
  border-bottom: none;
}
</style>
