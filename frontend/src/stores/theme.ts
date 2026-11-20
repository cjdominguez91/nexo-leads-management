import { defineStore } from 'pinia'
import { ref } from 'vue'

const STORAGE_KEY = 'nexo_theme'

function systemPrefersDark() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

function applyTheme(isDark: boolean) {
  document.documentElement.classList.toggle('dark', isDark)
}

export const useThemeStore = defineStore('theme', () => {
  const stored = localStorage.getItem(STORAGE_KEY)
  const isDark = ref(stored ? stored === 'dark' : systemPrefersDark())
  applyTheme(isDark.value)

  function toggle() {
    isDark.value = !isDark.value
    localStorage.setItem(STORAGE_KEY, isDark.value ? 'dark' : 'light')
    applyTheme(isDark.value)
  }

  return { isDark, toggle }
})
