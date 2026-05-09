<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <component
    :is="tag"
    class="btn"
    :class="[`kind-${kind}`, `size-${size}`, { loading }]"
    v-bind="$attrs"
  >
    <slot />
  </component>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    kind?: 'primary' | 'accent' | 'ghost' | 'soft' | 'warm' | 'danger'
    size?: 'sm' | 'md' | 'lg'
    tag?: string
    loading?: boolean
  }>(),
  { kind: 'primary', size: 'md', tag: 'button', loading: false }
)
</script>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--bbf-s-2);
  font-family: var(--bbf-font);
  font-weight: 600;
  border: none;
  border-radius: var(--bbf-r-md);
  cursor: pointer;
  text-decoration: none;
  transition: background 0.15s, color 0.15s, opacity 0.15s, transform 0.1s;
  white-space: nowrap;
  line-height: 1;
}
.btn:active:not(:disabled) { transform: scale(0.98); }
.btn:disabled, .btn.loading { opacity: 0.55; cursor: not-allowed; }

.size-sm { font-size: 12px; padding: 5px 12px; height: 28px; }
.size-md { font-size: 13px; padding: 7px 16px; height: 34px; }
.size-lg { font-size: 14px; padding: 9px 22px; height: 40px; }

.kind-primary  { background: var(--bbf-primary);    color: #fff; }
.kind-primary:hover:not(:disabled)  { background: var(--bbf-primary-2); }

.kind-accent   { background: var(--bbf-ink);        color: var(--bbf-bg); }
.kind-accent:hover:not(:disabled)   { opacity: 0.88; }

.kind-ghost    { background: transparent; color: var(--bbf-ink-2); border: 1px solid var(--bbf-line-strong); }
.kind-ghost:hover:not(:disabled)    { background: var(--bbf-surface-2); color: var(--bbf-ink); }

.kind-soft     { background: var(--bbf-surface-2);  color: var(--bbf-ink-2); }
.kind-soft:hover:not(:disabled)     { background: var(--bbf-surface-3); color: var(--bbf-ink); }

.kind-warm     { background: var(--bbf-warm);       color: #fff; }
.kind-warm:hover:not(:disabled)     { background: var(--bbf-warm-2); }

.kind-danger   { background: var(--bbf-danger-soft); color: var(--bbf-danger); border: 1px solid transparent; }
.kind-danger:hover:not(:disabled)   { background: var(--bbf-danger); color: #fff; }
</style>
