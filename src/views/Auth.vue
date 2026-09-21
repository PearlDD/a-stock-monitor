<template>
  <main class="auth"><h1>盯盘助手</h1><p>登录后管理仅属于你的自选股与提醒。</p>
    <van-form @submit="submit"><van-cell-group inset>
      <van-field v-model="email" name="email" type="email" label="邮箱" placeholder="name@example.com" required />
      <van-field v-model="password" name="password" type="password" label="密码" placeholder="至少 8 位" required />
    </van-cell-group><div class="actions"><van-button round block type="primary" native-type="submit" :loading="loading">{{ registering ? '注册' : '登录' }}</van-button>
      <van-button plain round block @click="registering = !registering">{{ registering ? '已有账号，去登录' : '新用户注册' }}</van-button></div>
    <p class="hint">注册后可能需要先在邮箱中确认账号。</p></van-form>
  </main>
</template>
<script setup>
import { ref } from 'vue'
import { showToast } from 'vant'
import { supabase } from '../lib/supabase'
const email = ref(''); const password = ref(''); const loading = ref(false); const registering = ref(false)
const submit = async () => { loading.value = true; try {
  if (password.value.length < 8) throw new Error('密码至少需要 8 位')
  const result = registering.value
    ? await supabase.auth.signUp({
      email: email.value,
      password: password.value,
      // Keep confirmation links on whichever approved deployment served this page.
      options: { emailRedirectTo: `${window.location.origin}/` },
    })
    : await supabase.auth.signInWithPassword({ email: email.value, password: password.value })
  if (result.error) throw result.error
  showToast(registering.value ? '注册成功，请检查邮箱确认链接' : '登录成功')
} catch (error) { showToast(error.message || '操作失败') } finally { loading.value = false } }
</script>
<style scoped>.auth{max-width:440px;margin:70px auto;padding:24px}.auth h1{text-align:center}.auth p{color:#666;text-align:center}.actions{margin:24px 16px;display:grid;gap:12px}.hint{font-size:12px}</style>
