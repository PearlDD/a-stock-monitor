<template>
  <div class="stock-detail">
    <van-nav-bar :title="stockName" left-arrow @click-left="$router.back()" />

    <!-- Price Header -->
    <div class="price-header" :class="priceClass">
      <div class="current-price">{{ currencySymbol }}{{ formatPrice(quote.price) }}</div>
      <div class="price-info">
        {{ formatChange(quote.change_pct) }}
        <span v-if="quote.prev_close">
          昨收 {{ currencySymbol }}{{ formatPrice(quote.prev_close) }}
        </span>
      </div>
      <div class="data-delay">数据可能存在延迟，仅供参考</div>
    </div>

    <!-- Tabs -->
    <van-tabs v-model:active="activeTab" sticky>
      <van-tab title="行情">
        <div class="info-grid">
          <div class="info-item">
            <span class="label">今开</span>
            <span>{{ currencySymbol }}{{ formatPrice(quote.open) }}</span>
          </div>
          <div class="info-item">
            <span class="label">最高</span>
            <span class="price-up">{{ currencySymbol }}{{ formatPrice(quote.high) }}</span>
          </div>
          <div class="info-item">
            <span class="label">最低</span>
            <span class="price-down">{{ currencySymbol }}{{ formatPrice(quote.low) }}</span>
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

        <!-- Financial Summary Card -->
        <div v-if="financials" class="financial-card">
          <div class="card-title">财务摘要</div>
          <div class="info-grid">
            <div class="info-item">
              <span class="label">总市值</span>
              <span>{{ formatAmount(financials.market_cap) }}</span>
            </div>
            <div class="info-item">
              <span class="label">市盈率</span>
              <span>{{ financials.pe_ratio ? financials.pe_ratio.toFixed(1) : '-' }}</span>
            </div>
            <div class="info-item">
              <span class="label">市净率</span>
              <span>{{ financials.pb_ratio ? financials.pb_ratio.toFixed(2) : '-' }}</span>
            </div>
            <div class="info-item">
              <span class="label">营收</span>
              <span>{{ formatAmount(financials.revenue * 10000) }}</span>
            </div>
            <div class="info-item">
              <span class="label">净利润</span>
              <span>{{ formatAmount(financials.net_profit * 10000) }}</span>
            </div>
          </div>
        </div>

        <!-- 5-day price chart -->
        <div class="chart-section" v-if="history.length">
          <div class="card-title">近5日走势</div>
          <canvas ref="chartCanvas" width="340" height="160"></canvas>
        </div>
      </van-tab>

      <van-tab title="资讯">
        <van-list
          v-model:loading="newsLoading"
          :finished="newsFinished"
          finished-text="没有更多了"
          @load="loadMoreNews"
        >
          <van-empty v-if="!news.length && !newsLoading" description="暂无资讯" />
          <div v-for="item in news" :key="item.url" class="news-item">
            <a :href="item.url" target="_blank" rel="noopener">{{ item.title }}</a>
            <div class="news-meta">
              {{ item.source }} · {{ formatTime(item.publish_time) }}
            </div>
          </div>
        </van-list>
      </van-tab>

      <van-tab title="公告">
        <van-empty v-if="!announcements.length" description="暂无公告" />
        <div v-for="(item, idx) in announcements" :key="idx" class="news-item">
          <a v-if="item.url" :href="item.url" target="_blank" rel="noopener">{{ item.title }}</a>
          <span v-else>{{ item.title }}</span>
          <div class="news-meta">{{ item.date }}</div>
        </div>
      </van-tab>
    </van-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import {
  getQuotes, getStockNews,
  getFinancials, getPriceHistory, getAnnouncements,
} from '../api'

const route = useRoute()
const code = route.params.code
const stockName = ref(code)
const activeTab = ref(0)

const quote = ref({ price: 0, change_pct: 0, prev_close: 0, open: 0, high: 0, low: 0, volume: 0, amount: 0, currency: 'CNY' })
const news = ref([])
const financials = ref(null)
const history = ref([])
const announcements = ref([])
const newsLoading = ref(false)
const newsFinished = ref(false)
const newsPage = ref(0)
const chartCanvas = ref(null)

const priceClass = ref('price-flat')
const currencySymbol = computed(() => quote.value.currency === 'USD' || !/^\d{6}$/.test(code) ? '$' : '¥')

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

const loadMoreNews = async () => {
  try {
    newsLoading.value = true
    const limit = 20
    const { data } = await getStockNews(code, limit + newsPage.value * limit)
    const all = data.news
    if (all.length <= news.value.length || all.length < limit) {
      newsFinished.value = true
    }
    news.value = all
    newsPage.value++
  } catch (e) {
    newsFinished.value = true
  } finally {
    newsLoading.value = false
  }
}

const fetchFinancials = async () => {
  try {
    const { data } = await getFinancials(code)
    financials.value = data.financials
  } catch (e) { /* ignore */ }
}

const fetchHistory = async () => {
  try {
    const { data } = await getPriceHistory(code, 5)
    history.value = data.history || []
    await nextTick()
    drawChart()
  } catch (e) { /* ignore */ }
}

const fetchAnnouncements = async () => {
  try {
    const { data } = await getAnnouncements(code, 20)
    announcements.value = data.announcements || []
  } catch (e) { /* ignore */ }
}

const drawChart = () => {
  const canvas = chartCanvas.value
  if (!canvas || !history.value.length) return
  const ctx = canvas.getContext('2d')
  const w = canvas.width
  const h = canvas.height
  const padding = { top: 10, right: 10, bottom: 25, left: 50 }
  const plotW = w - padding.left - padding.right
  const plotH = h - padding.top - padding.bottom

  ctx.clearRect(0, 0, w, h)

  const closes = history.value.map(d => d.close)
  const minP = Math.min(...closes) * 0.998
  const maxP = Math.max(...closes) * 1.002
  const range = maxP - minP || 1

  // Draw grid
  ctx.strokeStyle = '#eee'
  ctx.lineWidth = 0.5
  for (let i = 0; i <= 4; i++) {
    const y = padding.top + (plotH / 4) * i
    ctx.beginPath()
    ctx.moveTo(padding.left, y)
    ctx.lineTo(w - padding.right, y)
    ctx.stroke()
    ctx.fillStyle = '#999'
    ctx.font = '10px sans-serif'
    ctx.textAlign = 'right'
    ctx.fillText((maxP - (range / 4) * i).toFixed(2), padding.left - 4, y + 3)
  }

  // Draw line
  ctx.beginPath()
  ctx.strokeStyle = closes[closes.length - 1] >= closes[0] ? '#e74c3c' : '#2ecc71'
  ctx.lineWidth = 2
  for (let i = 0; i < closes.length; i++) {
    const x = padding.left + (plotW / (closes.length - 1 || 1)) * i
    const y = padding.top + plotH - ((closes[i] - minP) / range) * plotH
    if (i === 0) ctx.moveTo(x, y)
    else ctx.lineTo(x, y)
  }
  ctx.stroke()

  // Draw dates
  ctx.fillStyle = '#999'
  ctx.font = '10px sans-serif'
  ctx.textAlign = 'center'
  history.value.forEach((d, i) => {
    const x = padding.left + (plotW / (closes.length - 1 || 1)) * i
    ctx.fillText(d.date.slice(5), x, h - 5)
  })
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
  fetchFinancials()
  fetchHistory()
  fetchAnnouncements()
})
</script>

<style scoped>
.price-header {
  padding: 20px 16px;
  background: #fff;
}
.current-price { font-size: 32px; font-weight: 700; }
.price-info { font-size: 14px; margin-top: 4px; color: #666; }
.data-delay { font-size: 11px; color: #bbb; margin-top: 4px; }
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
.financial-card {
  margin: 12px 0;
}
.card-title {
  padding: 12px 16px 4px;
  font-size: 15px;
  font-weight: 600;
  color: #333;
}
.chart-section {
  background: #fff;
  padding: 0 16px 16px;
  margin: 8px 0;
}
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
