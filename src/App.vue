<template>
  <div v-if="!configured" class="config-error">缺少 VITE_SUPABASE_URL 或 VITE_SUPABASE_ANON_KEY，无法启动。</div>
  <Auth v-else-if="!session" />
  <div v-else class="app-container">
    <div v-if="isDemoMode" class="demo-banner">演示模式</div>
    <div v-if="webAlerts.length" class="web-alert" role="alert">
      <span>🔔 网页提醒：{{ webAlerts[0].rule.stock_name || webAlerts[0].rule.stock_code }}（{{ webAlerts[0].rule.stock_code }}）已触发{{ webAlerts.length > 1 ? `，另有 ${webAlerts.length - 1} 条` : '' }}</span>
      <button @click="dismissWebAlerts">我知道了</button>
    </div>
    <router-view @market-status="onMarketStatus" />
    <van-tabbar v-model="active" route>
      <van-tabbar-item to="/" icon="home-o">自选股</van-tabbar-item>
      <van-tabbar-item to="/sectors" icon="chart-trending-o">板块</van-tabbar-item>
      <van-tabbar-item to="/alerts" icon="bell">提醒</van-tabbar-item>
      <van-tabbar-item to="/settings" icon="setting-o">设置</van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { getQuotes, getAlertNotifications } from './api'
import Auth from './views/Auth.vue'
import { supabase, isSupabaseConfigured } from './lib/supabase'

const active = ref(0)
const isDemoMode = ref(false)
const configured = isSupabaseConfigured
const session = ref(null)
const webAlerts = ref([])
let subscription
let reminderTimer

const onMarketStatus = (status) => {
  isDemoMode.value = status === 'demo'
}

const checkDemoMode = async () => {
  try {
    const { data } = await getQuotes(['000001'])
    isDemoMode.value = data.market_status === 'demo'
  } catch {
    // ignore — will check again when data loads
  }
}

const dismissedStorageKey = 'dismissed-web-alerts'
const checkWebAlerts = async () => {
  try {
    const { data } = await getAlertNotifications()
    const dismissed = new Set(JSON.parse(localStorage.getItem(dismissedStorageKey) || '[]'))
    webAlerts.value = (data.notifications || []).filter((item) => !dismissed.has(item.id))
  } catch {
    // A failed reminder check must never prevent the application from loading.
  }
}

const dismissWebAlerts = () => {
  const dismissed = new Set(JSON.parse(localStorage.getItem(dismissedStorageKey) || '[]'))
  webAlerts.value.forEach((item) => dismissed.add(item.id))
  localStorage.setItem(dismissedStorageKey, JSON.stringify([...dismissed].slice(-100)))
  webAlerts.value = []
}

const startSignedInChecks = () => {
  checkDemoMode()
  checkWebAlerts()
  if (!reminderTimer) reminderTimer = window.setInterval(checkWebAlerts, 30000)
}

onMounted(async () => {
  if (!configured) return
  session.value = (await supabase.auth.getSession()).data.session
  subscription = supabase.auth.onAuthStateChange((_event, next) => {
    session.value = next
    if (next) startSignedInChecks()
    else { window.clearInterval(reminderTimer); reminderTimer = undefined; webAlerts.value = [] }
  }).data.subscription
  if (session.value) startSignedInChecks()
})
onUnmounted(() => { subscription?.unsubscribe(); window.clearInterval(reminderTimer) })
</script>

<style>
.app-container {
  padding-bottom: 50px;
  min-height: 100vh;
  background: #f7f8fa;
}
.demo-banner {
  background: #fff3cd;
  color: #856404;
  text-align: center;
  padding: 4px 0;
  font-size: 12px;
  position: sticky;
  top: 0;
  z-index: 1000;
}
.web-alert { display: flex; gap: 10px; align-items: center; justify-content: space-between; background: #fff3cd; color: #6d4c00; padding: 10px 14px; font-size: 14px; position: sticky; top: 0; z-index: 1001; }
.web-alert button { flex: none; border: 0; border-radius: 4px; color: #fff; background: #1989fa; padding: 5px 8px; }
.config-error { padding: 32px; color: #b42318; }
</style>
