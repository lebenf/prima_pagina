<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <teleport to="body">
    <div class="modal-backdrop fixed inset-0 bg-black bg-opacity-50 z-50 flex items-start justify-center p-4 md:p-8" @click.self="$emit('close')">
      <div class="modal-container bg-white rounded-lg shadow-2xl w-full max-w-3xl max-h-screen flex flex-col">
        <!-- Header -->
        <div class="modal-header flex items-start justify-between p-6 border-b border-gray-200 flex-shrink-0">
          <div>
            <h2 class="font-serif text-2xl font-bold" style="font-family: Georgia, 'Times New Roman', serif;">
              {{ digest?.title || t('frontpage.latestDigest') }}
            </h2>
            <p class="text-sm text-gray-500 mt-1">
              {{ t('frontpage.digestArticles', { count: digest?.article_count || 0 }) }}
              <span v-if="digest?.llm_provider"> · {{ t('frontpage.digestGenerated', { provider: digest.llm_provider }) }}</span>
            </p>
          </div>
          <button
            @click="$emit('close')"
            class="text-gray-400 hover:text-gray-700 text-2xl leading-none ml-4 flex-shrink-0"
            :aria-label="t('common.cancel')"
          >×</button>
        </div>

        <!-- Content — server-sanitized HTML -->
        <div class="modal-body overflow-y-auto flex-1 p-6">
          <DigestContent v-if="digest" :digest="digest" />
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Digest } from '@/api/digest'
import DigestContent from '@/components/digest/DigestContent.vue'

defineProps<{ digest: Digest | null }>()
defineEmits<{ close: [] }>()
const { t } = useI18n()

onMounted(() => { document.body.style.overflow = 'hidden' })
onUnmounted(() => { document.body.style.overflow = '' })
</script>
