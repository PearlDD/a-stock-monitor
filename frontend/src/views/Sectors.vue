<template>
  <div class="sectors">
    <van-nav-bar title="板块轮动" />

    <!-- Sector Rotation Predictions -->
    <van-cell-group title="板块轮动预测" inset>
      <van-loading v-if="loadingSectors" style="padding: 20px; text-align: center;" />
      <van-empty v-else-if="!predictions.length && !sectorError" description="暂无预测数据" />
      <div v-else-if="sectorError" class="error-text">{{ sectorError }}</div>
      <div v-else>
        <div v-for="(p, idx) in predictions" :key="idx" class="sector-card">
          <div class="sector-name">{{ p.sector }}</div>
          <div class="sector-reason">{{ p.reason }}</div>
          <div v-if="p.leaders && p.leaders.length" class="sector-leaders">
            <span class="leader-label">龙头股:</span>
            <span
              v-for="leader in p.leaders"
              :key="leader.code"
              class="leader-tag"
              @click="goToStock(leader.code)"
            >
              {{ leader.name || leader.code }}
            </span>
          </div>
        </div>
      </div>
    </van-cell-group>

    <!-- Capital Flow Top -->
    <van-cell-group title="大资金流入排行" inset style="margin-top: 12px;">
      <van-loading v-if="loadingFlow" style="padding: 20px; text-align: center;" />
      <van-empty v-else-if="!capitalFlowStocks.length" description="暂无数据" />
      <div v-else>
        <div
          v-for="stock in capitalFlowStocks"
          :key="stock.code"
          class="flow-card"
          @click="goToStock(stock.code)"
        >
          <div class="flow-left">
            <div class="flow-name">{{ stock.name }}</div>
            <div class="flow-code">{{ stock.code }}</div>
          </div>
          <div class="flow-right">
            <div class="flow-amount">{{ formatAmount(stock.net_inflow) }}</div>
            <div :class="['flow-pct', stock.change_pct >= 0 ? 'red' : 'green']">
              {{ stock.change_pct >= 0 ? '+' : '' }}{{ stock.change_pct.toFixed(2) }}%
            </div>
          </div>
        </div>
      </div>
    </van-cell-group>

    <div class="disclaimer">
      ⚠️ 以上由AI预测，仅供参考，不构成投资建议
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getSectorRotation, getCapitalFlowTop } from '../api'

const router = useRouter()
const predictions = ref([])
const capitalFlowStocks = ref([])
const loadingSectors = ref(true)
const loadingFlow = ref(true)
const sectorError = ref('')

const fetchSectors = async () => {
  loadingSectors.value = true
  try {
    const { data } = await getSectorRotation()
    predictions.value = data.predictions || []
    sectorError.value = data.error || ''
  } catch (e) {
    sectorError.value = '获取板块数据失败'
  } finally {
    loadingSectors.value = false
  }
}

const fetchCapitalFlow = async () => {
  loadingFlow.value = true
  try {
    const { data } = await getCapitalFlowTop()
    capitalFlowStocks.value = (data.stocks || []).slice(0, 20)
  } catch (e) {
    /* ignore */
  } finally {
    loadingFlow.value = false
  }
}

const goToStock = (code) => {
  if (code) router.push(`/stock/${code}`)
}

const formatAmount = (amount) => {
  const yi = amount / 1e8
  if (Math.abs(yi) >= 1) return yi.toFixed(2) + '亿'
  const wan = amount / 1e4
  return wan.toFixed(0) + '万'
}

onMounted(() => {
  fetchSectors()
  fetchCapitalFlow()
})
</script>

<style scoped>
.sectors { padding-top: 8px; }
.sector-card {
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
}
.sector-name {
  font-size: 16px;
  font-weight: 600;
}
.sector-reason {
  font-size: 13px;
  color: #666;
  margin-top: 4px;
  line-height: 1.4;
}
.sector-leaders { margin-top: 6px; }
.leader-label {
  font-size: 12px;
  color: #999;
}
.leader-tag {
  display: inline-block;
  background: #eef5ff;
  color: #1989fa;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  margin-left: 6px;
  cursor: pointer;
}
.flow-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
}
.flow-name { font-size: 15px; font-weight: 500; }
.flow-code { font-size: 12px; color: #999; }
.flow-right { text-align: right; }
.flow-amount { font-size: 14px; font-weight: 600; color: #e74c3c; }
.flow-pct { font-size: 13px; }
.flow-pct.red { color: #e74c3c; }
.flow-pct.green { color: #2ecc71; }
.error-text {
  padding: 20px 16px;
  color: #999;
  text-align: center;
}
.disclaimer {
  text-align: center;
  font-size: 12px;
  color: #999;
  padding: 20px 16px;
}
</style>
