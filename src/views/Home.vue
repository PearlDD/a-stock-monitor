<template>
  <div class="home">
    <van-nav-bar title="自选股">
      <template #right>
        <van-icon name="plus" size="20" @click="showSearch = true" />
      </template>
    </van-nav-bar>
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
              {{ currencySymbol(stock) }}{{ formatPrice(stock.price) }}
            </div>
            <div class="stock-change" :class="priceClass(stock)">
              {{ formatChange(stock.change_pct) }}
            </div>
          </div>
        </div>
      </van-list>
    </van-pull-refresh>

    <van-popup v-model:show="showSearch" position="top" :style="{ height: '80%' }">
      <van-search
        v-model="searchQuery"
        placeholder="输入名称或代码（如 Apple、AAPL、600519）"
        show-action
        @search="onSearch"
        @cancel="showSearch = false"
      />
      <van-list :finished="true" finished-text="">
        <van-cell
          v-for="item in searchResults"
          :key="item.code"
          :title="`${item.name} (${item.code})`"
          :label="item.market"
          is-link
          @click="onAddStock(item)"
        />
        <van-empty v-if="searchQuery && !searchResults.length && !searching" description="无搜索结果" />
      </van-list>
    </van-popup>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { showToast } from 'vant'
import { getWatchlist, getQuotes, searchStocks, addToWatchlist } from '../api'

const stocks = ref([])
const loading = ref(false)
const refreshing = ref(false)

const showSearch = ref(false)
const searchQuery = ref('')
const searchResults = ref([])
const searching = ref(false)

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

const onSearch = async () => {
  const q = searchQuery.value.trim()
  if (!q) return
  try {
    searching.value = true
    const { data } = await searchStocks(q)
    searchResults.value = data.results || []
  } finally {
    searching.value = false
  }
}

const onAddStock = async (item) => {
  try {
    await addToWatchlist({ code: item.code, name: item.name, market: item.market })
    showToast(`已添加 ${item.name}`)
    showSearch.value = false
    searchQuery.value = ''
    searchResults.value = []
    await fetchData()
  } catch {
    showToast('添加失败')
  }
}

// Chinese convention: red=up, green=down
const priceClass = (stock) => {
  if (stock.change_pct > 0) return 'price-up'
  if (stock.change_pct < 0) return 'price-down'
  return 'price-flat'
}

const formatPrice = (p) => (p || 0).toFixed(2)
const currencySymbol = (stock) => stock.currency === 'USD' || stock.market === 'US' ? '$' : '¥'
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
