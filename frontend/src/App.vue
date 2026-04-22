<template>
  <OfflineBanner />
  <UpdatePrompt />
  <RouterView />
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router'
import OfflineBanner from '@/components/common/OfflineBanner.vue'
import UpdatePrompt from '@/components/common/UpdatePrompt.vue'
</script>
