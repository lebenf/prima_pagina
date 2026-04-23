<!-- Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later -->
<template>
  <div class="skeleton-container space-y-6 mt-4">
    <!-- Hero skeleton -->
    <div class="skeleton-hero p-4 border-b-2 border-gray-200">
      <div class="skeleton-line h-3 w-1/5" />
      <div class="skeleton-line h-10 w-4/5 mt-3" />
      <div class="skeleton-line h-10 w-3/5 mt-1" />
      <div class="skeleton-line h-4 w-full mt-4" />
      <div class="skeleton-line h-4 w-2/3 mt-1" />
      <div class="skeleton-line h-4 w-1/3 mt-3" />
    </div>

    <!-- Second row skeleton -->
    <div class="skeleton-second-row grid grid-cols-1 md:grid-cols-3 gap-4">
      <div v-for="i in 3" :key="i" class="p-4 border-r border-gray-200 last:border-0">
        <div class="skeleton-line h-3 w-1/3" />
        <div class="skeleton-line h-6 w-full mt-2" />
        <div class="skeleton-line h-6 w-4/5 mt-1" />
        <div class="skeleton-line h-3 w-1/2 mt-3" />
      </div>
    </div>

    <!-- Columns skeleton -->
    <div class="skeleton-columns grid grid-cols-1 md:grid-cols-3 gap-4 border-t-2 border-gray-200 pt-4">
      <div v-for="i in 3" :key="i" class="space-y-4">
        <div class="skeleton-line h-4 w-1/2" />
        <div v-for="j in 3" :key="j" class="pb-3 border-b border-gray-100 last:border-0">
          <div class="skeleton-line h-4 w-full" />
          <div class="skeleton-line h-4 w-3/4 mt-1" />
          <div class="skeleton-line h-3 w-1/3 mt-2" />
        </div>
      </div>
    </div>
  </div>
</template>
