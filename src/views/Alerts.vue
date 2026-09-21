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
          <div class="alert-info">
            {{ alertTypeLabel(alert.alert_type) }} · {{ alert.threshold }}
            <span v-if="alert.triggered_at && !alert.enabled" class="triggered-badge">
              已触发 {{ alert.triggered_at }}
            </span>
          </div>
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
        <van-field v-model="form.stock_code" label="股票代码" placeholder="如 AAPL 或 600519" required />
        <van-field v-model="form.stock_name" label="股票名称（可选）" placeholder="如 Apple；系统会校验代码" />
        <van-field name="alert_type" label="提醒类型">
          <template #input>
            <van-radio-group v-model="form.alert_type" direction="horizontal">
              <van-radio name="price_target">目标价</van-radio>
              <van-radio name="limit_up">涨停</van-radio>
              <van-radio name="limit_down">跌停</van-radio>
              <van-radio name="volume_spike">量能异动</van-radio>
            </van-radio-group>
          </template>
        </van-field>
        <van-field
          v-model.number="form.threshold"
          :label="targetPriceLabel"
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
  alert_type: 'price_target',
  threshold: 0,
  direction: 'above',
})

const thresholdHint = computed(() => {
  const hints = {
    price_target: '目标价格，如 1800',
    limit_up: '不需要填写',
    limit_down: '不需要填写',
    volume_spike: '倍数，如 3（3倍均量）',
  }
  return hints[form.value.alert_type] || ''
})

const targetPriceLabel = computed(() => (/^\D/.test(form.value.stock_code.trim()) ? '阈值（美元）' : '阈值（人民币）'))

const alertTypeLabel = (type) => {
  const labels = {
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
  const code = form.value.stock_code.trim()
  if (!code) return showToast('请填写股票代码，例如 AAPL')
  if (form.value.alert_type === 'price_target' && (!Number.isFinite(form.value.threshold) || form.value.threshold <= 0)) {
    return showToast('请在“阈值”中填写大于 0 的目标价格')
  }
  try {
    await createAlert({ ...form.value, stock_code: code })
    showToast('提醒已添加')
    showAdd.value = false
    form.value = { stock_code: '', stock_name: '', alert_type: 'price_target', threshold: 0, direction: 'above' }
    await fetchAlerts()
  } catch (error) {
    showToast(error.response?.data?.error || '添加失败，请检查股票代码和阈值')
  }
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
.triggered-badge {
  display: inline-block;
  background: #f5f5f5;
  color: #e74c3c;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  margin-left: 6px;
}
</style>
