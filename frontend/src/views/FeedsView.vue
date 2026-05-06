<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="feeds-page">
    <AdminFeeds :is-admin="auth.isAdmin" />
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import AdminFeeds from '@/components/admin/AdminFeeds.vue'

const auth = useAuthStore()
</script>

<style scoped>
.feeds-page {
  padding: 1.5rem;
}
</style>
