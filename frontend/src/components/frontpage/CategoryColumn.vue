<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="category-column">
    <header class="category-header mb-3 pb-1 border-b-2" :style="{ borderColor: headerColor }">
      <h3 class="text-xs font-black uppercase tracking-widest" :style="{ color: headerColor }">
        {{ column.category_name }}
      </h3>
    </header>
    <ul class="space-y-3">
      <li
        v-for="event in column.events"
        :key="event.id"
        class="pb-3 border-b border-gray-200 last:border-0 last:pb-0"
      >
        <EventCard
          size="compact"
          :event="event"
          @click="$emit('event-click', event)"
          @vote-changed="(vote, id) => $emit('vote-changed', vote, id)"
        />
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import EventCard from './EventCard.vue'
import type { Event, EventFrontPageColumn } from '@/api/events'

const props = defineProps<{ column: EventFrontPageColumn }>()
defineEmits<{ 'event-click': [event: Event]; 'vote-changed': [vote: number, eventId: string] }>()

const headerColor = computed(() => {
  const hue = props.column.category_slug
    .split('')
    .reduce((acc, c) => acc + c.charCodeAt(0), 0) % 360
  return `hsl(${hue}, 60%, 35%)`
})
</script>
