<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <OfflineBanner />
  <UpdatePrompt />
  <RouterView />
  <SearchModal />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { RouterView } from 'vue-router'
import OfflineBanner from '@/components/common/OfflineBanner.vue'
import UpdatePrompt from '@/components/common/UpdatePrompt.vue'
import SearchModal from '@/components/common/SearchModal.vue'
import { useSearchStore } from '@/stores/search'

const searchStore = useSearchStore()

function handleGlobalKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault()
    searchStore.isOpen ? searchStore.close() : searchStore.open()
  }
}

onMounted(() => window.addEventListener('keydown', handleGlobalKeydown))
onUnmounted(() => window.removeEventListener('keydown', handleGlobalKeydown))
</script>
