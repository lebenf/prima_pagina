<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <span class="status-badge" :class="[`kind-${kind}`, `size-${size}`]">
    <slot />
  </span>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    kind?: 'ok' | 'warn' | 'info' | 'mute' | 'danger' | 'warm' | 'primary'
    size?: 'sm' | 'md'
  }>(),
  { kind: 'mute', size: 'md' }
)
</script>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  font-family: var(--bbf-mono);
  font-variant-numeric: tabular-nums;
  font-weight: 500;
  border-radius: 999px;
  white-space: nowrap;
  line-height: 1;
}

.size-sm { font-size: 11px; padding: 2px 7px; }
.size-md { font-size: 12px; padding: 3px 9px; }

.kind-ok      { color: var(--bbf-ok);       background: var(--bbf-ok-soft); }
.kind-warn    { color: var(--bbf-warn);     background: var(--bbf-warn-soft); }
.kind-info    { color: var(--bbf-info);     background: var(--bbf-info-soft); }
.kind-mute    { color: var(--bbf-mute);     background: var(--bbf-mute-soft); }
.kind-danger  { color: var(--bbf-danger);   background: var(--bbf-danger-soft); }
.kind-warm    { color: var(--bbf-warm-2);   background: var(--bbf-warm-soft); }
.kind-primary { color: var(--bbf-primary);  background: var(--bbf-primary-soft); }
</style>
