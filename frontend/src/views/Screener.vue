<template>
  <div class="screener">
    <van-nav-bar title="AI选股" />

    <!-- Search bar -->
    <div class="search-section">
      <van-search
        v-model="query"
        placeholder="输入选股条件，如：低市盈率大盘股"
        @search="onSearch"
      />
    </div>

    <!-- Quick filter chips -->
    <div class="preset-chips">
      <van-tag
        v-for="p in presets" :key="p.name"
        :type="selectedPreset === p.name ? 'primary' : 'default'"
        size="large"
        round
        class="chip"
        @click="onPreset(p.name)"
      >
        {{ p.name }}
      </van-tag>
    </div>

    <!-- Results -->
    <van-loading v-if="loading" class="loading" />

    <div v-if="error" class="error-msg">
      <van-icon name="warning-o" /> {{ error }}
    </div>

    <van-empty v-if="!loading && !stocks.length && !error" description="输入条件或选择预设开始筛选" />

    <div
      v-for="stock in stocks" :key="stock.code"
      class="stock-card"
      @click="$router.push(`/stock/${stock.code}`)"
    >
      <div class="stock-left">
        <div class="stock-name">{{ stock.name }}</div>
        <div class="stock-code">{{ stock.code }}</div>
      </div>
      <div class="stock-right">
        <div class="stock-price" :class="priceClass(stock)">
          ¥{{ (stock.price || 0).toFixed(2) }}
        </div>
        <div class="stock-change" :class="priceClass(stock)">
          {{ formatChange(stock.change_pct) }}
        </div>
      </div>
    </div>

    <div v-if="stocks.length" class="disclaimer">
      ⚠️ 以上由AI筛选，仅供参考，不构成投资建议
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { showToast } from 'vant'
import { screenStocks, getPresets } from '../api'

const query = ref('')
const presets = ref([])
const selectedPreset = ref('')
const stocks = ref([])
const loading = ref(false)
const error = ref('')

const fetchPresets = async () => {
  try {
    const { data } = await getPresets()
    presets.value = data.presets || []
  } catch (e) { /* ignore */ }
}

const onSearch = async () => {
  if (!query.value.trim()) return
  selectedPreset.value = ''
  loading.value = true
  error.value = ''
  try {
    const { data } = await screenStocks({ query: query.value })
    stocks.value = data.stocks || []
    if (data.error) error.value = data.error
  } catch (e) {
    showToast('筛选请求失败')
  } finally {
    loading.value = false
  }
}

const onPreset = async (name) => {
  selectedPreset.value = name
  query.value = ''
  loading.value = true
  error.value = ''
  try {
    const { data } = await screenStocks({ preset: name })
    stocks.value = data.stocks || []
    if (data.error) error.value = data.error
  } catch (e) {
    showToast('筛选请求失败')
  } finally {
    loading.value = false
  }
}

const priceClass = (stock) => {
  if (stock.change_pct > 0) return 'price-up'
  if (stock.change_pct < 0) return 'price-down'
  return 'price-flat'
}

const formatChange = (pct) => {
  if (!pct) return '0.00%'
  return (pct > 0 ? '+' : '') + pct.toFixed(2) + '%'
}

onMounted(fetchPresets)
</script>

<style scoped>
.search-section { padding: 0 8px; }
.preset-chips {
  padding: 8px 16px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.chip { cursor: pointer; }
.loading { text-align: center; padding: 40px 0; }
.error-msg {
  text-align: center;
  padding: 20px;
  color: #e74c3c;
  font-size: 14px;
}
.stock-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  margin: 8px 12px;
  background: #fff;
  border-radius: 8px;
  min-height: 44px;
}
.stock-name { font-size: 17px; font-weight: 600; }
.stock-code { font-size: 13px; color: #999; margin-top: 4px; }
.stock-right { text-align: right; }
.stock-price { font-size: 18px; font-weight: 700; }
.stock-change { font-size: 14px; margin-top: 2px; }
.price-up { color: #e74c3c; }
.price-down { color: #2ecc71; }
.price-flat { color: #999; }
.disclaimer {
  text-align: center;
  font-size: 12px;
  color: #999;
  padding: 16px;
}
</style>
