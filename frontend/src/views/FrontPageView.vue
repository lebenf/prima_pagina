<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="frontpage-container max-w-6xl mx-auto px-4 py-4">

    <!-- Digest banner -->
    <DigestBanner
      v-if="store.showDigest && store.digest"
      :digest="store.digest"
      @dismiss="store.dismissDigest()"
      @open="digestModalOpen = true"
      @retry="handleGenerateDigest"
    />

    <!-- Newspaper header -->
    <header class="newspaper-header mb-4">
      <div class="flex items-center justify-between text-xs text-gray-500 mb-1">
        <span>{{ formattedDate }}</span>
        <span v-if="store.lastUpdated" class="text-gray-400">
          {{ t('frontpage.lastUpdated', { time: lastUpdatedLabel }) }}
        </span>
      </div>
      <h1 class="masthead">Prima Pagina</h1>
      <div class="flex items-center justify-end mt-2">
        <button
          @click="handleGenerateDigest"
          :disabled="store.isGeneratingDigest"
          class="flex items-center gap-2 text-sm px-3 py-1.5 rounded border border-gray-300 hover:border-gray-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <svg v-if="store.isGeneratingDigest" class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
          </svg>
          <span>{{ store.isGeneratingDigest ? t('frontpage.generating') : t('frontpage.generateDigest') }}</span>
        </button>
      </div>
    </header>

    <!-- Loading state: show generating banner -->
    <div v-if="store.isGeneratingDigest" class="text-sm text-center text-gray-500 py-2 mb-4 bg-blue-50 rounded">
      {{ t('frontpage.generatingDetail') }}
    </div>

    <!-- Skeleton during first load -->
    <FrontPageSkeleton v-if="store.isLoading && !store.data" />

    <template v-else-if="store.data">
      <div class="newspaper-rule" />

      <!-- Hero + second row -->
      <section class="top-section mb-4">
        <EventCard
          v-if="store.data.hero"
          size="hero"
          :event="store.data.hero"
          @click="openEvent(store.data.hero!)"
          @vote-changed="onVoteChanged"
        />

        <div v-if="store.data.second_row.length" class="second-row mt-4">
          <EventCard
            v-for="event in store.data.second_row"
            :key="event.id"
            size="row"
            :event="event"
            @click="openEvent(event)"
            @vote-changed="onVoteChanged"
          />
        </div>
      </section>

      <div v-if="store.data.columns.length" class="newspaper-rule" />

      <!-- Category columns -->
      <section v-if="store.data.columns.length" class="columns-section">
        <CategoryColumn
          v-for="col in store.data.columns"
          :key="col.category_slug"
          :column="col"
          @event-click="openEvent"
          @vote-changed="onVoteChanged"
        />
      </section>
    </template>

    <!-- Empty state -->
    <div v-else-if="!store.isLoading" class="empty-state text-center py-16 text-gray-500">
      <p class="mb-4">{{ t('frontpage.noArticles') }}</p>
      <RouterLink to="/reader" class="text-blue-600 hover:underline">
        {{ t('frontpage.goToReader') }}
      </RouterLink>
    </div>

    <!-- Error state -->
    <div v-if="store.error" class="mt-4 p-3 bg-red-50 text-red-700 text-sm rounded">
      {{ store.error }}
    </div>

    <!-- Digest modal -->
    <DigestModal
      v-if="digestModalOpen && store.digest"
      :digest="store.digest"
      @close="digestModalOpen = false"
    />

  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter, RouterLink } from 'vue-router'
import { useFrontPageStore } from '@/stores/frontpage'
import type { Event } from '@/api/events'
import DigestBanner from '@/components/frontpage/DigestBanner.vue'
import DigestModal from '@/components/frontpage/DigestModal.vue'
import FrontPageSkeleton from '@/components/frontpage/FrontPageSkeleton.vue'
import EventCard from '@/components/frontpage/EventCard.vue'
import CategoryColumn from '@/components/frontpage/CategoryColumn.vue'
import '@/assets/newspaper.css'

const store = useFrontPageStore()
const { t, locale } = useI18n()
const router = useRouter()
const digestModalOpen = ref(false)

onMounted(async () => {
  await store.load(locale.value)
  store.startAutoRefresh()
})

onUnmounted(() => {
  store.stopAutoRefresh()
})

function openEvent(event: Event) {
  router.push({ name: 'event', params: { id: event.id } })
}

function onVoteChanged(vote: number, eventId: string) {
  const update = (e: Event | null | undefined) => {
    if (e?.id === eventId) e.user_vote = vote
  }
  update(store.data?.hero)
  store.data?.second_row.forEach(update)
  store.data?.columns.forEach(col => col.events.forEach(update))
}

async function handleGenerateDigest() {
  await store.generateDigest()
}

const formattedDate = computed(() =>
  new Intl.DateTimeFormat(locale.value, {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  }).format(new Date())
)

const lastUpdatedLabel = computed(() => {
  if (!store.lastUpdated) return ''
  const diffMin = Math.floor((Date.now() - store.lastUpdated.getTime()) / 60_000)
  if (diffMin < 1) return new Intl.RelativeTimeFormat(locale.value, { numeric: 'auto' }).format(0, 'minute')
  return new Intl.RelativeTimeFormat(locale.value, { numeric: 'always' }).format(-diffMin, 'minute')
})
</script>
