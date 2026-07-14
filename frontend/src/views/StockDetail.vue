<template>
  <div class="stock-detail">
    <van-nav-bar :title="stockName" left-arrow @click-left="$router.back()" />

    <!-- Price Header -->
    <div class="price-header" :class="priceClass">
      <div class="current-price">¥{{ formatPrice(quote.price) }}</div>
      <div class="price-info">
        {{ formatChange(quote.change_pct) }}
        <span v-if="quote.prev_close">
          昨收 ¥{{ formatPrice(quote.prev_close) }}
        </span>
      </div>
    </div>

    <!-- Tabs -->
    <van-tabs v-model:active="activeTab" sticky>
      <van-tab title="行情">
        <div class="info-grid">
          <div class="info-item">
            <span class="label">今开</span>
            <span>¥{{ formatPrice(quote.open) }}</span>
          </div>
          <div class="info-item">
            <span class="label">最高</span>
            <span class="price-up">¥{{ formatPrice(quote.high) }}</span>
          </div>
          <div class="info-item">
            <span class="label">最低</span>
            <span class="price-down">¥{{ formatPrice(quote.low) }}</span>
          </div>
          <div class="info-item">
            <span class="label">成交量</span>
            <span>{{ formatVolume(quote.volume) }}</span>
          </div>
          <div class="info-item">
            <span class="label">成交额</span>
            <span>{{ formatAmount(quote.amount) }}</span>
          </div>
        </div>
      </van-tab>

      <van-tab title="资讯">
        <van-empty v-if="!news.length" description="暂无资讯" />
        <div v-for="item in news" :key="item.url" class="news-item">
          <a :href="item.url" target="_blank" rel="noopener">{{ item.title }}</a>
          <div class="news-meta">
            {{ item.source }} · {{ formatTime(item.publish_time) }}
          </div>
        </div>
      </van-tab>

      <van-tab title="分析">
        <div class="info-grid" v-if="info">
          <div class="info-item">
            <span class="label">行业</span>
            <span>{{ info.sector || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="label">上市日期</span>
            <span>{{ info.list_date || '-' }}</span>
          </div>
        </div>
        <van-empty v-else description="暂无分析数据" />
      </van-tab>
    </van-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getQuotes, getStockInfo, getStockNews } from '../api'

const route = useRoute()
const code = route.params.code
const stockName = ref(code)
const activeTab = ref(0)

const quote = ref({ price: 0, change_pct: 0, prev_close: 0, open: 0, high: 0, low: 0, volume: 0, amount: 0 })
const news = ref([])
const info = ref(null)

const priceClass = ref('price-flat')

const fetchQuote = async () => {
  try {
    const { data } = await getQuotes([code])
    if (data.quotes.length) {
      quote.value = data.quotes[0]
      stockName.value = data.quotes[0].name || code
      priceClass.value = data.quotes[0].change_pct > 0 ? 'price-up' : data.quotes[0].change_pct < 0 ? 'price-down' : 'price-flat'
    }
  } catch (e) { /* ignore */ }
}

const fetchNews = async () => {
  try {
    const { data } = await getStockNews(code, 20)
    news.value = data.news
  } catch (e) { /* ignore */ }
}

const fetchInfo = async () => {
  try {
    const { data } = await getStockInfo(code)
    info.value = data.info
  } catch (e) { /* ignore */ }
}

const formatPrice = (p) => (p || 0).toFixed(2)
const formatChange = (pct) => {
  if (!pct) return '0.00%'
  return (pct > 0 ? '+' : '') + pct.toFixed(2) + '%'
}
const formatVolume = (v) => {
  if (!v) return '-'
  if (v >= 1e8) return (v / 1e8).toFixed(2) + '亿'
  if (v >= 1e4) return (v / 1e4).toFixed(0) + '万'
  return v.toFixed(0)
}
const formatAmount = (a) => {
  if (!a) return '-'
  if (a >= 1e8) return (a / 1e8).toFixed(2) + '亿'
  if (a >= 1e4) return (a / 1e4).toFixed(0) + '万'
  return a.toFixed(0)
}
const formatTime = (t) => {
  if (!t) return ''
  return t.replace('T', ' ').substring(0, 16)
}

onMounted(() => {
  fetchQuote()
  fetchNews()
  fetchInfo()
})
</script>

<style scoped>
.price-header {
  padding: 20px 16px;
  background: #fff;
}
.current-price { font-size: 32px; font-weight: 700; }
.price-info { font-size: 14px; margin-top: 4px; color: #666; }
.price-up { color: #e74c3c; }
.price-down { color: #2ecc71; }
.price-flat { color: #999; }
.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1px;
  background: #f0f0f0;
  margin: 8px 0;
}
.info-item {
  background: #fff;
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  font-size: 15px;
  min-height: 44px;
  align-items: center;
}
.info-item .label { color: #999; }
.news-item {
  padding: 14px 16px;
  border-bottom: 1px solid #f0f0f0;
  min-height: 44px;
}
.news-item a {
  color: #333;
  text-decoration: none;
  font-size: 15px;
  line-height: 1.5;
}
.news-meta { font-size: 12px; color: #999; margin-top: 6px; }
</style>
