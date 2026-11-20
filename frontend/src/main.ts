import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import router from './router'
import { useThemeStore } from './stores/theme'
import './style.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)

// Aplica la clase .dark en <html> antes del primer render, para que no
// haya parpadeo del tema equivocado al cargar.
useThemeStore()

window.addEventListener('nexo:session-expired', () => {
  if (router.currentRoute.value.name !== 'login') {
    router.push({ name: 'login' })
  }
})

app.mount('#app')
