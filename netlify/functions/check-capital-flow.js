import { sendPush } from './shared/pushplus.js'
import { isTradingHours } from './shared/trading-hours.js'

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
    const url = `http://qt.gtimg.cn/q=${POPULAR_CODES.join(',')}`
    const res = await fetch(url)
    const text = await res.text()

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

    if (alerts.length > 0) {
      let content = '以下热门股大幅波动：\n\n'
      for (const a of alerts) {
        const sign = a.change_pct > 0 ? '+' : ''
        content += `${a.name}(${a.code}) ¥${a.price.toFixed(2)} ${sign}${a.change_pct.toFixed(2)}%\n`
      }
      content += '\n⚠️ 仅供参考，不构成投资建议'
      await sendPush('📈 热门股异动提醒', content)
    }
  } catch (err) {
    console.error('Capital flow check failed:', err.message)
  }
}

export const config = {
  schedule: '*/5 1-3,5-7 * * 1-5',
}
