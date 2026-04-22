import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useUiStore = defineStore('ui', () => {
  const sidebarOpen = ref(true)
  const sidebarCollapsed = ref(false)

  function toggleSidebar() {
    sidebarOpen.value = !sidebarOpen.value
  }

  function toggleCollapse() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  return { sidebarOpen, sidebarCollapsed, toggleSidebar, toggleCollapse }
})
