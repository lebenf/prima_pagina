<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="digest-view max-w-3xl mx-auto px-4 py-6">
    <LoadingSpinner v-if="loading" class="mt-16" />

    <div v-else-if="error" class="mt-4 p-3 bg-red-50 text-red-700 text-sm rounded">
      {{ error }}
    </div>

    <template v-else-if="digest">
      <RouterLink :to="{ name: 'digests' }" class="digest-view__back">← {{ t('digest.title') }}</RouterLink>

      <header class="digest-view__header">
        <h1 class="digest-view__title">{{ digest.title || t('digest.title') }}</h1>
        <p class="digest-view__meta">
          {{ t('digest.period', { start: formatDate(digest.period_start), end: formatDate(digest.period_end) }) }}
        </p>
        <p class="digest-view__meta">
          {{ t('digest.articles', { count: digest.article_count }) }}
          <span v-if="digest.llm_provider"> · {{ t('digest.provider', { provider: digest.llm_provider }) }}</span>
        </p>
        <button class="digest-view__delete" @click="confirmingDelete = true">{{ t('common.delete') }}</button>
      </header>

      <DigestContent :digest="digest" />
    </template>

    <ConfirmDialog
      v-if="confirmingDelete"
      :title="t('digest.title')"
      :message="t('digest.deleteConfirm')"
      @confirm="handleDelete"
      @cancel="confirmingDelete = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { digestApi, type Digest } from '@/api/digest'
import DigestContent from '@/components/digest/DigestContent.vue'
import ConfirmDialog from '@/components/admin/ConfirmDialog.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const digest = ref<Digest | null>(null)
const loading = ref(false)
const error = ref('')
const confirmingDelete = ref(false)

function formatDate(iso: string) {
  return new Intl.DateTimeFormat(locale.value, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(iso))
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await digestApi.get(route.params.id as string)
    digest.value = res.data
  } catch {
    error.value = t('common.error')
  } finally {
    loading.value = false
  }
}

async function handleDelete() {
  if (!digest.value) return
  await digestApi.delete(digest.value.id)
  router.push({ name: 'digests' })
}

onMounted(load)
</script>

<style scoped>
.digest-view__back {
  display: inline-block;
  font-size: 0.85rem;
  color: #2563eb;
  text-decoration: none;
  margin-bottom: 1rem;
}
.digest-view__back:hover {
  text-decoration: underline;
}
.digest-view__header {
  border-bottom: 2px solid #1f2937;
  padding-bottom: 1rem;
  margin-bottom: 1.5rem;
  position: relative;
}
.digest-view__title {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 2rem;
  font-weight: 900;
  line-height: 1.2;
  margin-bottom: 0.5rem;
}
.digest-view__meta {
  font-size: 0.85rem;
  color: #6b7280;
  margin: 0.15rem 0;
}
.digest-view__delete {
  margin-top: 0.75rem;
  padding: 0.35rem 0.75rem;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  background: none;
  cursor: pointer;
  font-size: 0.8rem;
  color: #dc2626;
}
.digest-view__delete:hover {
  background: #fef2f2;
}
</style>
