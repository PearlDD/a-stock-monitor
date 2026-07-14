<template>
  <div class="home">
    <van-nav-bar title="自选股" />
    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <van-list
        v-model:loading="loading"
        :finished="true"
        finished-text=""
      >
        <van-empty v-if="!stocks.length && !loading" description="暂无自选股" />
        <div
          v-for="stock in stocks"
          :key="stock.code"
          class="stock-card"
          @click="$router.push(`/stock/${stock.code}`)"
        >
          <div class="stock-left">
            <div class="stock-name">{{ stock.name }}</div>
            <div class="stock-code">{{ stock.code }}</div>
          </div>
          <div class="stock-right">
            <div class="stock-price" :class="priceClass(stock)">
              ¥{{ formatPrice(stock.price) }}
            </div>
            <div class="stock-change" :class="priceClass(stock)">
              {{ formatChange(stock.change_pct) }}
            </div>
          </div>
        </div>
      </van-list>
    </van-pull-refresh>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getWatchlist, getQuotes } from '../api'

const stocks = ref([])
const loading = ref(false)
const refreshing = ref(false)

const fetchData = async () => {
  try {
    loading.value = true
    const { data } = await getWatchlist()
    const codes = data.stocks.map(s => s.code)
    if (codes.length) {
      const { data: quotesData } = await getQuotes(codes)
      const quoteMap = {}
      quotesData.quotes.forEach(q => { quoteMap[q.code] = q })
      stocks.value = data.stocks.map(s => ({
        ...s,
        ...(quoteMap[s.code] || { price: 0, change_pct: 0 }),
      }))
    } else {
      stocks.value = []
    }
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

const onRefresh = () => fetchData()

// Chinese convention: red=up, green=down
const priceClass = (stock) => {
  if (stock.change_pct > 0) return 'price-up'
  if (stock.change_pct < 0) return 'price-down'
  return 'price-flat'
}

const formatPrice = (p) => (p || 0).toFixed(2)
const formatChange = (pct) => {
  if (!pct) return '0.00%'
  return (pct > 0 ? '+' : '') + pct.toFixed(2) + '%'
}

onMounted(fetchData)
</script>

<style scoped>
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
</style>
