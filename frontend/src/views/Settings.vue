<template>
  <div class="settings">
    <van-nav-bar title="设置" />

    <van-cell-group title="推送设置" inset>
      <van-field
        v-model="token"
        label="PushPlus Token"
        placeholder="请输入Token"
        type="password"
      />
      <van-cell title="保存Token">
        <template #right-icon>
          <van-button size="small" type="primary" @click="saveToken">保存</van-button>
        </template>
      </van-cell>
      <van-cell title="测试推送">
        <template #right-icon>
          <van-button size="small" :loading="testing" @click="onTestPush">发送测试</van-button>
        </template>
      </van-cell>
    </van-cell-group>

    <van-cell-group title="推送配额" inset style="margin-top: 12px;">
      <van-cell title="今日已用" :value="`${quota.used} / ${quota.limit}`" />
      <van-cell title="剩余额度" :value="quota.remaining + ''" />
      <van-progress
        :percentage="quotaPct"
        :color="quotaPct > 80 ? '#e74c3c' : '#1989fa'"
        stroke-width="8"
        style="padding: 8px 16px;"
      />
    </van-cell-group>

    <van-cell-group title="系统信息" inset style="margin-top: 12px;">
      <van-cell title="时区" value="Asia/Shanghai" />
      <van-cell title="版本" value="0.1.0" />
    </van-cell-group>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { showToast } from 'vant'
import { getSettings, updateSettings, testPush, getPushQuota } from '../api'

const token = ref('')
const testing = ref(false)
const quota = ref({ used: 0, limit: 195, remaining: 195 })

const quotaPct = computed(() => {
  if (!quota.value.limit) return 0
  return Math.round((quota.value.used / quota.value.limit) * 100)
})

const fetchSettings = async () => {
  try {
    const { data } = await getSettings()
    if (data.pushplus_token_set) {
      token.value = '••••••••'
    }
  } catch (e) { /* ignore */ }
}

const fetchQuota = async () => {
  try {
    const { data } = await getPushQuota()
    quota.value = data
  } catch (e) { /* ignore */ }
}

const saveToken = async () => {
  if (!token.value || token.value === '••••••••') {
    showToast('请输入有效Token')
    return
  }
  await updateSettings({ pushplus_token: token.value })
  showToast('Token已保存')
}

const onTestPush = async () => {
  testing.value = true
  try {
    await testPush()
    showToast('测试消息已发送')
    await fetchQuota()
  } catch (e) {
    showToast('发送失败，请检查Token')
  } finally {
    testing.value = false
  }
}

onMounted(() => {
  fetchSettings()
  fetchQuota()
})
</script>

<style scoped>
.settings {
  padding-top: 8px;
}
</style>
