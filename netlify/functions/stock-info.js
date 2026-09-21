import { buildTencentUrl, parseTencentResponse } from './shared/tencent.js'
import { jsonResponse, handleOptions } from './shared/cors.js'
import { requireUser } from './shared/auth.js'
import { normalizeStockCode } from './shared/validation.js'
import { fetchTencentGBK } from './shared/tencent.js'

export default async (req) => {
  if (req.method === 'OPTIONS') return handleOptions(req)
  const auth = await requireUser(req)
  if (auth.response) return auth.response

  const url = new URL(req.url)
  // Match paths like /api/stocks/600519/info, /api/stocks/600519/news, etc.
  const match = url.pathname.match(/\/api\/stocks\/([^/]+)\/(\w+)/)
  if (!match) {
    return jsonResponse({ error: '无效路径' }, 400)
  }

  const code = normalizeStockCode(match[1])
  if (!code) return jsonResponse({ error: '股票代码必须为六码数字' }, 400, req)
  const action = match[2]

  try {
    if (action === 'info') {
      return await getStockInfo(code)
    }
    if (action === 'news') {
      const limit = parseInt(url.searchParams.get('limit') || '10', 10)
      return await getStockNews(code, limit)
    }
    if (action === 'financials') {
      return await getStockFinancials(code)
    }
    if (action === 'history') {
      const days = parseInt(url.searchParams.get('days') || '5', 10)
      return await getStockHistory(code, days)
    }
    if (action === 'announcements') {
      return await getStockAnnouncements(code)
    }

    return jsonResponse({ error: '未知操作' }, 404)
  } catch (err) {
    return jsonResponse({ error: err.message }, 500)
  }
}

async function getStockInfo(code) {
  const tencentUrl = buildTencentUrl([code])
  const text = await fetchTencentGBK(tencentUrl)
  const quotes = parseTencentResponse(text)

  if (!quotes.length) {
    return jsonResponse({ error: '未找到股票数据' }, 404)
  }

  const q = quotes[0]
  return jsonResponse({
    info: {
      code: q.code,
      name: q.name,
      price: q.price,
      prev_close: q.prev_close,
      open: q.open,
      high: q.high,
      low: q.low,
      volume: q.volume,
      amount: q.amount,
      change_pct: q.change_pct,
      pe_ratio: q.pe_ratio,
      market_cap: q.market_cap,
    },
  })
}

async function getStockNews(code, limit) {
  // Tencent Finance doesn't provide news API; return placeholder
  return jsonResponse({
    news: [],
    message: '新闻数据暂不可用',
  })
}

async function getStockFinancials(code) {
  const tencentUrl = buildTencentUrl([code])
  const text = await fetchTencentGBK(tencentUrl)
  const quotes = parseTencentResponse(text)

  if (!quotes.length) {
    return jsonResponse({ financials: null })
  }

  const q = quotes[0]
  return jsonResponse({
    financials: {
      market_cap: q.market_cap,
      pe_ratio: q.pe_ratio,
      pb_ratio: null,
      revenue: null,
      net_profit: null,
    },
  })
}

async function getStockHistory(code, days) {
  // Use Tencent day-level kline: minimal implementation
  // qt.gtimg.cn doesn't have easy kline API; use current quote as single point
  const tencentUrl = buildTencentUrl([code])
  const text = await fetchTencentGBK(tencentUrl)
  const quotes = parseTencentResponse(text)

  if (!quotes.length) {
    return jsonResponse({ history: [] })
  }

  const q = quotes[0]
  const today = new Date().toISOString().slice(0, 10)
  return jsonResponse({
    history: [
      { date: today, open: q.open, high: q.high, low: q.low, close: q.price, volume: q.volume },
    ],
  })
}

async function getStockAnnouncements(code) {
  return jsonResponse({
    announcements: [],
    message: '公告数据暂不可用',
  })
}

export const config = {
  path: '/api/stocks/:code/:action',
}
