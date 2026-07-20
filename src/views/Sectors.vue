<template>
  <div class="sectors">
    <van-nav-bar title="板块资金" />

    <!-- Capital Flow Top -->
    <van-cell-group title="大资金流入排行" inset>
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
      ⚠️ 数据可能存在延迟，仅供参考，不构成投资建议
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getCapitalFlowTop } from '../api'

const router = useRouter()
const capitalFlowStocks = ref([])
const loadingFlow = ref(true)

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
  fetchCapitalFlow()
})
</script>

<style scoped>
.sectors { padding-top: 8px; }
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
.disclaimer {
  text-align: center;
  font-size: 12px;
  color: #999;
  padding: 20px 16px;
}
</style>
