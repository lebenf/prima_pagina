// Copyright (C) 2026 Lorenzo Benfeati — SPDX-License-Identifier: AGPL-3.0-or-later
import { ref, watchEffect } from 'vue'

const THEME_KEY = 'bbf.theme'

function getInitialTheme(): 'light' | 'dark' {
  const stored = localStorage.getItem(THEME_KEY) as 'light' | 'dark' | null
  if (stored) return stored
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

const theme = ref<'light' | 'dark'>(getInitialTheme())

watchEffect(() => {
  if (theme.value === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark')
  } else {
    document.documentElement.removeAttribute('data-theme')
  }
  localStorage.setItem(THEME_KEY, theme.value)
})

export function useTheme() {
  return {
    theme,
    toggle: () => { theme.value = theme.value === 'dark' ? 'light' : 'dark' },
    isDark: () => theme.value === 'dark',
  }
}
