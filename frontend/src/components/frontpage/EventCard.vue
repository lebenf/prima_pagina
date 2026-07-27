<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <article
    class="event-card cursor-pointer"
    :class="sizeClass"
    @click="$emit('click')"
  >
    <span v-if="event.tags?.length" class="category-label">{{ event.tags[0] }}</span>

    <component :is="titleTag" class="event-title">{{ event.title }}</component>

    <p v-if="size !== 'compact' && plainSynopsis" class="event-synopsis">
      {{ plainSynopsis }}
    </p>

    <footer class="event-meta">
      <EventSourceBadge v-if="event.source_count > 1" :count="event.source_count" />
      <span v-if="event.category_name" class="category-name">{{ event.category_name }}</span>
      <RelativeTime :date="event.last_activity_at" />
      <VoteButtons
        target="event"
        :target-id="event.id"
        :initial-vote="event.user_vote ?? 0"
        :compact="true"
        @click.stop
        @vote-changed="(vote, id) => $emit('vote-changed', vote, id)"
      />
    </footer>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import RelativeTime from '@/components/common/RelativeTime.vue'
import VoteButtons from '@/components/common/VoteButtons.vue'
import EventSourceBadge from '@/components/events/EventSourceBadge.vue'
import type { Event } from '@/api/events'

const props = defineProps<{ event: Event; size: 'hero' | 'row' | 'compact' }>()
defineEmits<{ click: []; 'vote-changed': [vote: number, eventId: string] }>()

const sizeClass = computed(() => `event-card--${props.size}`)
const titleTag = computed(() => (props.size === 'hero' ? 'h2' : props.size === 'row' ? 'h3' : 'p'))

const plainSynopsis = computed(() => {
  if (!props.event.synopsis) return ''
  const div = document.createElement('div')
  div.innerHTML = props.event.synopsis
  return div.textContent || div.innerText || ''
})
</script>

<style scoped>
.event-card {
  display: block;
}
.category-label {
  display: block;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #6b7280;
  margin-bottom: 0.25rem;
}
.event-title {
  font-family: Georgia, 'Times New Roman', serif;
  font-weight: 700;
  line-height: 1.25;
  margin: 0 0 0.5rem;
}
.event-card--hero .event-title {
  font-size: 2.5rem;
  font-weight: 900;
}
.event-card--row .event-title {
  font-size: 1.125rem;
}
.event-card--compact .event-title {
  font-size: 0.875rem;
  font-weight: 700;
  margin-bottom: 0.25rem;
}
.event-synopsis {
  color: #374151;
  font-size: 0.95rem;
  line-height: 1.5;
  margin-bottom: 0.5rem;
}
.event-card--row .event-synopsis {
  font-size: 0.85rem;
  -webkit-line-clamp: 2;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.event-card--hero .event-synopsis {
  -webkit-line-clamp: 3;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.event-meta {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.75rem;
  color: #9ca3af;
  flex-wrap: wrap;
}
.category-name {
  color: #6b7280;
}
</style>
