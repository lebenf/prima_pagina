<template>
  <Transition name="slide-up">
    <div v-if="needsRefresh" class="update-prompt" role="alert">
      <p class="update-message">{{ t('pwa.updateAvailable') }}</p>
      <div class="update-actions">
        <button class="btn-update" @click="updateNow">{{ t('pwa.updateNow') }}</button>
        <button class="btn-dismiss" @click="dismiss">{{ t('pwa.updateLater') }}</button>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

// needsRefresh and updateServiceWorker come from vite-plugin-pwa
// Use dynamic import to avoid breaking tests/SSR environments
const needsRefresh = ref(false)
let _updateServiceWorker: ((reloadPage?: boolean) => Promise<void>) | null = null

if (typeof window !== 'undefined') {
  import('virtual:pwa-register/vue').then(({ useRegisterSW }) => {
    const { needRefresh, updateServiceWorker } = useRegisterSW()
    _updateServiceWorker = updateServiceWorker
    // sync reactive ref
    const stop = setInterval(() => {
      if (needRefresh.value) {
        needsRefresh.value = true
        clearInterval(stop)
      }
    }, 1000)
  }).catch(() => {
    // PWA not available in dev without HTTPS — silent fail
  })
}

async function updateNow() {
  if (_updateServiceWorker) {
    await _updateServiceWorker(true)
  } else {
    window.location.reload()
  }
}

function dismiss() {
  needsRefresh.value = false
}
</script>

<style scoped>
.update-prompt {
  position: fixed;
  bottom: 1.5rem;
  left: 50%;
  transform: translateX(-50%);
  background: #1a1a1a;
  color: white;
  border-radius: 8px;
  padding: 1rem 1.25rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  z-index: 9998;
  white-space: nowrap;
}

.update-message {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 600;
}

.update-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-update {
  padding: 0.375rem 0.875rem;
  border: none;
  border-radius: 4px;
  background: #3b82f6;
  color: white;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 600;
}

.btn-update:hover {
  background: #2563eb;
}

.btn-dismiss {
  padding: 0.375rem 0.875rem;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 4px;
  background: transparent;
  color: white;
  cursor: pointer;
  font-size: 0.8rem;
}

.btn-dismiss:hover {
  background: rgba(255, 255, 255, 0.1);
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.25s ease, opacity 0.25s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  transform: translate(-50%, 1rem);
  opacity: 0;
}
</style>
