<template>
  <div class="app-container">
    <router-view />
    <van-tabbar v-model="active" route>
      <van-tabbar-item to="/" icon="home-o">自选股</van-tabbar-item>
      <van-tabbar-item to="/alerts" icon="bell">提醒</van-tabbar-item>
      <van-tabbar-item to="/settings" icon="setting-o">设置</van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const active = ref(0)
</script>

<style>
.app-container {
  padding-bottom: 50px;
  min-height: 100vh;
  background: #f7f8fa;
}
</style>
