import { getSupabase } from './shared/supabase.js'
import { buildTencentUrl, parseTencentResponse } from './shared/tencent.js'
import { sendPush } from './shared/pushplus.js'

/**
 * Scheduled: daily digest at 07:05 UTC (= 15:05 CST, after market close).
 * Sends a summary of watchlist performance.
 */
export default async () => {
  const supabase = getSupabase()

  const { data: watchlist } = await supabase
    .from('watchlist')
    .select('code, name')

  if (!watchlist?.length) {
    console.log('Watchlist is empty, skipping digest')
    return
  }

  const codes = watchlist.map((s) => s.code)
  const tencentUrl = buildTencentUrl(codes)
  const res = await fetch(tencentUrl)
  const text = await res.text()
  const quotes = parseTencentResponse(text)

  if (!quotes.length) {
    console.log('No quote data, skipping digest')
    return
  }

  // Sort by change_pct descending
  quotes.sort((a, b) => b.change_pct - a.change_pct)

  const title = '📊 今日行情总结'
  let content = '今日自选股表现：\n\n'

  for (const q of quotes) {
    const arrow = q.change_pct > 0 ? '🔴' : q.change_pct < 0 ? '🟢' : '⚪'
    const sign = q.change_pct > 0 ? '+' : ''
    content += `${arrow} ${q.name} ¥${q.price.toFixed(2)} ${sign}${q.change_pct.toFixed(2)}%\n`
  }

  content += '\n⚠️ 仅供参考，不构成投资建议'

  await sendPush(title, content)
}

export const config = {
  schedule: '5 7 * * 1-5',
}
