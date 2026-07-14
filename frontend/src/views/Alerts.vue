<template>
  <div class="alerts">
    <van-nav-bar title="提醒设置">
      <template #right>
        <van-icon name="plus" size="20" @click="showAdd = true" />
      </template>
    </van-nav-bar>

    <van-empty v-if="!alerts.length" description="暂无提醒规则" />

    <van-swipe-cell v-for="alert in alerts" :key="alert.id">
      <div class="alert-card">
        <div class="alert-left">
          <div class="alert-stock">{{ alert.stock_name }} ({{ alert.stock_code }})</div>
          <div class="alert-info">{{ alertTypeLabel(alert.alert_type) }} · {{ alert.threshold }}</div>
        </div>
        <van-switch
          :model-value="alert.enabled"
          size="20"
          @update:model-value="(val) => toggleAlert(alert.id, val)"
        />
      </div>
      <template #right>
        <van-button
          square type="danger" text="删除"
          class="delete-btn"
          @click="onDelete(alert.id)"
        />
      </template>
    </van-swipe-cell>

    <!-- Add Alert Dialog -->
    <van-popup v-model:show="showAdd" position="bottom" round style="padding: 20px;">
      <van-form @submit="onSubmit">
        <van-field v-model="form.stock_code" label="股票代码" placeholder="如 600519" required />
        <van-field v-model="form.stock_name" label="股票名称" placeholder="如 贵州茅台" />
        <van-field name="alert_type" label="提醒类型">
          <template #input>
            <van-radio-group v-model="form.alert_type" direction="horizontal">
              <van-radio name="price_pct_change">涨跌幅</van-radio>
              <van-radio name="price_target">目标价</van-radio>
              <van-radio name="limit_up">涨停</van-radio>
              <van-radio name="limit_down">跌停</van-radio>
            </van-radio-group>
          </template>
        </van-field>
        <van-field
          v-model.number="form.threshold"
          label="阈值"
          type="number"
          :placeholder="thresholdHint"
        />
        <van-field v-if="form.alert_type === 'price_target'" name="direction" label="方向">
          <template #input>
            <van-radio-group v-model="form.direction" direction="horizontal">
              <van-radio name="above">高于</van-radio>
              <van-radio name="below">低于</van-radio>
            </van-radio-group>
          </template>
        </van-field>
        <div style="margin-top: 16px;">
          <van-button round block type="primary" native-type="submit">添加提醒</van-button>
        </div>
      </van-form>
    </van-popup>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { showToast } from 'vant'
import { getAlerts, createAlert, updateAlert, deleteAlert } from '../api'

const alerts = ref([])
const showAdd = ref(false)
const form = ref({
  stock_code: '',
  stock_name: '',
  alert_type: 'price_pct_change',
  threshold: 5,
  direction: 'above',
})

const thresholdHint = computed(() => {
  const hints = {
    price_pct_change: '涨跌幅百分比，如 5',
    price_target: '目标价格，如 1800',
    limit_up: '不需要填写',
    limit_down: '不需要填写',
  }
  return hints[form.value.alert_type] || ''
})

const alertTypeLabel = (type) => {
  const labels = {
    price_pct_change: '涨跌幅',
    price_target: '目标价',
    limit_up: '涨停',
    limit_down: '跌停',
    volume_spike: '量能异动',
  }
  return labels[type] || type
}

const fetchAlerts = async () => {
  const { data } = await getAlerts()
  alerts.value = data.alerts
}

const onSubmit = async () => {
  await createAlert(form.value)
  showToast('提醒已添加')
  showAdd.value = false
  form.value = { stock_code: '', stock_name: '', alert_type: 'price_pct_change', threshold: 5, direction: 'above' }
  await fetchAlerts()
}

const toggleAlert = async (id, enabled) => {
  await updateAlert(id, { enabled })
  await fetchAlerts()
}

const onDelete = async (id) => {
  await deleteAlert(id)
  showToast('已删除')
  await fetchAlerts()
}

onMounted(fetchAlerts)
</script>

<style scoped>
.alert-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  background: #fff;
  margin: 8px 12px;
  border-radius: 8px;
  min-height: 44px;
}
.alert-stock { font-size: 16px; font-weight: 600; }
.alert-info { font-size: 13px; color: #999; margin-top: 4px; }
.delete-btn { height: 100%; }
</style>
