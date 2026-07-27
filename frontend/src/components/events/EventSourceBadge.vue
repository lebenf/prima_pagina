<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <span class="event-source-badge">{{ t('events.sourceCount', { count }) }}</span>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

defineProps<{ count: number }>()
const { t } = useI18n()
</script>

<style scoped>
.event-source-badge {
  display: inline-flex;
  align-items: center;
  font-size: 0.7rem;
  font-weight: 600;
  color: #1d4ed8;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  padding: 0.1rem 0.5rem;
}
</style>
