<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <Teleport to="body">
    <div class="confirm-overlay" @click.self="$emit('cancel')">
      <div class="confirm-dialog" role="dialog" aria-modal="true">
        <h3 class="confirm-title">{{ title }}</h3>
        <p class="confirm-message">{{ message }}</p>
        <div class="confirm-actions">
          <button class="btn-secondary" @click="$emit('cancel')">{{ t('common.cancel') }}</button>
          <button class="btn-danger" @click="$emit('confirm')">{{ t('common.confirm') }}</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

defineProps<{ title: string; message: string }>()
defineEmits<{ confirm: []; cancel: [] }>()

const { t } = useI18n()
</script>

<style scoped>
.confirm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.confirm-dialog {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  max-width: 420px;
  width: 90%;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.confirm-title {
  font-size: 1.1rem;
  font-weight: 700;
  margin: 0 0 0.75rem;
  color: #1a1a1a;
}

.confirm-message {
  margin: 0 0 1.5rem;
  color: #444;
  line-height: 1.5;
}

.confirm-actions {
  display: flex;
  gap: 0.75rem;
  justify-content: flex-end;
}

.btn-secondary {
  padding: 0.5rem 1rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  background: white;
  cursor: pointer;
  font-size: 0.875rem;
}

.btn-secondary:hover {
  background: #f5f5f5;
}

.btn-danger {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  background: #dc2626;
  color: white;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 600;
}

.btn-danger:hover {
  background: #b91c1c;
}
</style>
