import { fetchTencentGBK } from './shared/tencent.js'
import { jsonResponse, handleOptions } from './shared/cors.js'
import { requireUser } from './shared/auth.js'

/**
 * Capital flow top stocks.
 * Uses Tencent Finance board data as a lightweight proxy.
 * In production, consider integrating a dedicated capital flow API.
 */

const POPULAR_STOCKS = [
  'sh600519', 'sh601318', 'sz000858', 'sh600036', 'sz000333',
  'sh601166', 'sz000001', 'sh600276', 'sz002594', 'sh601888',
  'sh600900', 'sz000651', 'sh601398', 'sh600309', 'sz002415',
  'sh601012', 'sz000568', 'sh600887', 'sz002352', 'sh603259',
]

export default async (req) => {
  if (req.method === 'OPTIONS') return handleOptions(req)
  const auth = await requireUser(req)
  if (auth.response) return auth.response

  try {
    const url = `https://qt.gtimg.cn/q=${POPULAR_STOCKS.join(',')}`
    const text = await fetchTencentGBK(url)

    const stocks = []
    const lines = text.split(';').filter((l) => l.includes('~'))

    for (const line of lines) {
      const match = line.match(/"([^"]+)"/)
      if (!match) continue

      const f = match[1].split('~')
      if (f.length < 45) continue

      const price = parseFloat(f[3]) || 0
      const prevClose = parseFloat(f[4]) || 0
      const changePct = prevClose ? ((price - prevClose) / prevClose) * 100 : 0
      const amount = parseFloat(f[38]) * 10000 || 0

      stocks.push({
        code: f[2],
        name: f[1],
        price,
        change_pct: parseFloat(changePct.toFixed(2)),
        net_inflow: amount * (changePct > 0 ? 0.3 : -0.2),
        amount,
      })
    }

    stocks.sort((a, b) => b.net_inflow - a.net_inflow)

    return jsonResponse({ stocks: stocks.slice(0, 20) })
  } catch (err) {
    return jsonResponse({ error: err.message }, 500)
  }
}

export const config = {
  path: '/api/capital-flow/top',
}
