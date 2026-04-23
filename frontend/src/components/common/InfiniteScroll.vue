<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div ref="sentinel" class="h-4">
    <slot v-if="loading">
      <div class="flex justify-center py-2">
        <div class="w-5 h-5 border-2 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
      </div>
    </slot>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'

const props = defineProps<{
  loading: boolean
  hasMore: boolean
}>()

const emit = defineEmits<{
  loadMore: []
}>()

const sentinel = ref<HTMLElement | null>(null)
let observer: IntersectionObserver | null = null

function setup() {
  if (!sentinel.value) return
  observer = new IntersectionObserver(
    ([entry]) => {
      if (entry.isIntersecting && props.hasMore && !props.loading) {
        emit('loadMore')
      }
    },
    { threshold: 0.1 },
  )
  observer.observe(sentinel.value)
}

onMounted(setup)
onUnmounted(() => observer?.disconnect())

watch(() => props.hasMore, (val) => {
  if (!val) observer?.disconnect()
})
</script>
