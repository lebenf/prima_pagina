<template>
  <time :datetime="date || ''" :title="fullDate">{{ relativeLabel }}</time>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{ date: string | null | undefined }>()
const { locale } = useI18n()

const now = ref(new Date())
let timer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  timer = setInterval(() => { now.value = new Date() }, 60_000)
})

onUnmounted(() => {
  if (timer !== null) { clearInterval(timer); timer = null }
})

const fullDate = computed(() => {
  if (!props.date) return ''
  return new Intl.DateTimeFormat(locale.value, {
    dateStyle: 'long', timeStyle: 'short',
  }).format(new Date(props.date))
})

const relativeLabel = computed(() => {
  if (!props.date) return ''
  const dt = new Date(props.date)
  const diffMs = now.value.getTime() - dt.getTime()
  const diffMin = Math.floor(diffMs / 60_000)
  const diffHours = Math.floor(diffMs / 3_600_000)
  const diffDays = Math.floor(diffMs / 86_400_000)

  const rtf = new Intl.RelativeTimeFormat(locale.value, { numeric: 'auto' })

  if (diffMin < 1) return rtf.format(0, 'minute')
  if (diffMin < 60) return rtf.format(-diffMin, 'minute')
  if (diffHours < 24) return rtf.format(-diffHours, 'hour')
  if (diffDays < 30) return rtf.format(-diffDays, 'day')
  // Fallback: formatted date
  return new Intl.DateTimeFormat(locale.value, { day: 'numeric', month: 'short' }).format(dt)
})
</script>
