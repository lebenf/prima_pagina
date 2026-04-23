<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="min-h-screen flex items-center justify-center bg-newspaper-bg px-4">
    <div class="text-center">
      <p class="font-serif text-8xl font-bold text-newspaper-accent">404</p>
      <h1 class="mt-4 text-2xl font-bold text-newspaper-text">Pagina non trovata</h1>
      <p class="mt-2 text-gray-500 text-sm">La pagina che cerchi non esiste.</p>
      <RouterLink
        :to="{ name: 'frontpage' }"
        class="mt-6 inline-block px-5 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 transition-colors"
      >
        Torna alla home
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>
