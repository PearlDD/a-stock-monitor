import { getSupabase } from './shared/supabase.js'
import { buildTencentUrl, parseTencentResponse, fetchTencentGBK } from './shared/tencent.js'
import { sendPush } from './shared/pushplus.js'
import { getUserPushToken } from './shared/push-settings.js'

export default async () => {
  const supabase = getSupabase()
  try {
    const { data: watchlist, error } = await supabase.from('watchlist').select('user_id, code, name').not('user_id', 'is', null)
    if (error) throw error
    const groups = new Map()
    for (const stock of watchlist || []) groups.set(stock.user_id, [...(groups.get(stock.user_id) || []), stock])
    for (const [userId, stocks] of groups) {
      const quotes = parseTencentResponse(await fetchTencentGBK(buildTencentUrl(stocks.map((stock) => stock.code))))
      if (!quotes.length) continue
      const token = await getUserPushToken(userId)
      if (!token) continue
      quotes.sort((a, b) => b.change_pct - a.change_pct)
      const content = `今日自选股表现：\n\n${quotes.map((q) => `${q.change_pct > 0 ? '🔴' : q.change_pct < 0 ? '🟢' : '⚪'} ${q.name} ${q.currency === 'USD' ? '$' : '¥'}${q.price.toFixed(2)} ${(q.change_pct > 0 ? '+' : '') + q.change_pct.toFixed(2)}%`).join('\n')}\n\n⚠️ 仅供参考，不构成投资建议`
      await sendPush('📊 今日行情总结', content, { token, userId })
    }
  } catch (error) { console.error('daily digest failed', error.message) }
}

export const config = { schedule: '5 7 * * 1-5' }
