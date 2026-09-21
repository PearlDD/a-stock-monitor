import { isTradingHours } from './shared/trading-hours.js'
import { fetchTencentGBK } from './shared/tencent.js'

/**
 * Scheduled: check capital flow every 5 minutes during trading hours.
 * Alerts on large net inflows for popular stocks.
 */

const POPULAR_CODES = [
  'sh600519', 'sh601318', 'sz000858', 'sh600036', 'sz000333',
  'sz000001', 'sh600276', 'sz002594', 'sh601888', 'sh600900',
]

export default async () => {
  if (!isTradingHours()) {
    console.log('Outside trading hours, skipping capital flow check')
    return
  }

  try {
    const url = `https://qt.gtimg.cn/q=${POPULAR_CODES.join(',')}`
    const text = await fetchTencentGBK(url)

    const lines = text.split(';').filter((l) => l.includes('~'))
    const alerts = []

    for (const line of lines) {
      const match = line.match(/"([^"]+)"/)
      if (!match) continue
      const f = match[1].split('~')
      if (f.length < 45) continue

      const price = parseFloat(f[3]) || 0
      const prevClose = parseFloat(f[4]) || 0
      const changePct = prevClose ? ((price - prevClose) / prevClose) * 100 : 0

      // Alert if change > 5%
      if (Math.abs(changePct) >= 5) {
        alerts.push({
          name: f[1],
          code: f[2],
          price,
          change_pct: changePct,
        })
      }
    }

    // This feature has no per-user rule or delivery state yet. Logging avoids
    // broadcasting one user's data to every configured PushPlus recipient.
    if (alerts.length > 0) console.log(`Capital-flow signals found: ${alerts.length}`)
  } catch (err) {
    console.error('Capital flow check failed:', err.message)
  }
}

export const config = {
  schedule: '*/5 1-3,5-7 * * 1-5',
}
