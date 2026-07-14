import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import 'vant/lib/index.css'
import App from './App.vue'

const routes = [
  { path: '/', name: 'home', component: () => import('./views/Home.vue') },
  { path: '/stock/:code', name: 'detail', component: () => import('./views/StockDetail.vue') },
  { path: '/alerts', name: 'alerts', component: () => import('./views/Alerts.vue') },
  { path: '/settings', name: 'settings', component: () => import('./views/Settings.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

const app = createApp(App)
app.use(router)
app.mount('#app')
