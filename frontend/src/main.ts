import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'
import { i18n, setLocale, detectBrowserLocale } from './i18n'

import './assets/main.css'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(i18n)

// Load the browser locale before mounting
setLocale(detectBrowserLocale()).then(() => {
  app.mount('#app')
})
