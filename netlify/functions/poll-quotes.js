import { getSupabase } from './shared/supabase.js'
import { buildTencentUrl, parseTencentResponse, fetchTencentGBK } from './shared/tencent.js'
import { sendPush } from './shared/pushplus.js'
import { getUserPushToken } from './shared/push-settings.js'
import { isMarketTradingHours } from './shared/trading-hours.js'

// Netlify scheduled functions are at-least-once. claim_alert_delivery makes the
// send reservation atomic across overlapping invocations.
export default async () => {
  const supabase = getSupabase()
  try {
    const { data: rules, error } = await supabase.from('alert_rules').select('*').eq('enabled', true).not('user_id', 'is', null)
    if (error) throw error
    const activeRules = (rules || []).filter((rule) => isMarketTradingHours(rule.stock_code))
    if (!activeRules.length) return

    const text = await fetchTencentGBK(buildTencentUrl([...new Set(activeRules.map((rule) => rule.stock_code))]))
    const quotes = new Map(parseTencentResponse(text).map((quote) => [quote.code, quote]))
    const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Shanghai' }).format(new Date())

    for (const rule of activeRules) {
      const quote = quotes.get(rule.stock_code)
      if (!quote || !evaluateAlert(rule, quote)) continue
      const { data: claimed, error: claimError } = await supabase.rpc('claim_alert_delivery', { p_rule_id: rule.id, p_date: today })
      if (claimError) { console.error('alert claim failed', rule.id, claimError.message); continue }
      if (!claimed) continue
      try {
        const token = await getUserPushToken(rule.user_id)
        const message = buildAlertMessage(rule, quote)
        // A PushPlus token is optional.  Record the delivery as handled so the
        // signed-in web client can show an in-app reminder instead of retrying
        // the same rule every minute forever.
        if (!token) {
          await supabase.rpc('finish_alert_delivery', { p_rule_id: rule.id, p_date: today, p_success: true })
          if (rule.alert_type === 'price_target') await supabase.from('alert_rules').update({ enabled: false, triggered_at: new Date().toISOString() }).eq('id', rule.id)
          continue
        }
        const sent = await sendPush(message.title, message.content, { token, userId: rule.user_id })
        if (!sent.success) throw new Error(sent.reason || 'PushPlus rejected request')
        await supabase.rpc('finish_alert_delivery', { p_rule_id: rule.id, p_date: today, p_success: true })
        if (rule.alert_type === 'price_target') await supabase.from('alert_rules').update({ enabled: false, triggered_at: new Date().toISOString() }).eq('id', rule.id)
      } catch (sendError) {
        console.error('alert delivery failed', rule.id, sendError.message)
        await supabase.rpc('finish_alert_delivery', { p_rule_id: rule.id, p_date: today, p_success: false, p_error: String(sendError.message).slice(0, 500) })
      }
    }
  } catch (error) { console.error('quote polling failed', error.message) }
}

function evaluateAlert(rule, quote) {
  if (!Number.isFinite(quote.price) || quote.price <= 0) return false
  if (rule.alert_type === 'price_target') return rule.direction === 'above' ? quote.price >= rule.threshold : quote.price <= rule.threshold
  if (rule.alert_type === 'limit_up') return quote.change_pct >= 9.8
  if (rule.alert_type === 'limit_down') return quote.change_pct <= -9.8
  return rule.alert_type === 'volume_spike' && quote.turnover_rate >= rule.threshold
}

function buildAlertMessage(rule, quote) {
  const name = rule.stock_name || rule.stock_code
  const labels = { price_target: '目标价提醒', limit_up: '涨停提醒', limit_down: '跌停提醒', volume_spike: '量能异动' }
  const currency = quote.currency === 'USD' ? '$' : '¥'
  let content = `${name}(${rule.stock_code})\n现价: ${currency}${quote.price.toFixed(2)}  涨跌: ${(quote.change_pct > 0 ? '+' : '') + quote.change_pct.toFixed(2)}%\n`
  if (rule.alert_type === 'price_target') content += `已${rule.direction === 'above' ? '突破' : '跌破'}目标价 ${currency}${rule.threshold}\n`
  return { title: `${labels[rule.alert_type]} · ${name}`, content: `${content}⚠️ 仅供参考，不构成投资建议` }
}

// Run every weekday minute; isMarketTradingHours limits API calls to each
// market's regular session (China and New York respectively).
export const config = { schedule: '* * * * 1-5' }
