<template>
  <div class="app-container">
    <div v-if="isDemoMode" class="demo-banner">演示模式</div>
    <router-view @market-status="onMarketStatus" />
    <van-tabbar v-model="active" route>
      <van-tabbar-item to="/" icon="home-o">自选股</van-tabbar-item>
      <van-tabbar-item to="/sectors" icon="chart-trending-o">板块</van-tabbar-item>
      <van-tabbar-item to="/screen" icon="search">选股</van-tabbar-item>
      <van-tabbar-item to="/alerts" icon="bell">提醒</van-tabbar-item>
      <van-tabbar-item to="/settings" icon="setting-o">设置</van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getQuotes } from './api'

const active = ref(0)
const isDemoMode = ref(false)

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

onMounted(checkDemoMode)
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
</style>
