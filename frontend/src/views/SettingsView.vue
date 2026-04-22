<template>
  <div class="p-6">
    <h1 class="font-serif text-2xl font-bold text-newspaper-text mb-4">
      {{ t('nav.settings') }}
    </h1>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>
