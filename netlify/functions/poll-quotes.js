import { getSupabase } from './shared/supabase.js'
import { buildTencentUrl, parseTencentResponse } from './shared/tencent.js'
import { sendPush } from './shared/pushplus.js'
import { isTradingHours } from './shared/trading-hours.js'

/**
 * Scheduled: poll quotes every minute during trading hours.
 * Fetches real-time quotes for stocks with active alert rules,
 * evaluates alerts, sends PushPlus notifications when triggered.
 *
 * Cron: every minute during UTC 1:00-7:59 Mon-Fri
 * (= ~9:00-15:59 CST, covers both trading sessions with buffer)
 */
export default async () => {
  if (!isTradingHours()) {
    console.log('Outside trading hours, skipping poll')
    return
  }

  const supabase = getSupabase()

  // Get all enabled alert rules
  const { data: rules, error: rulesErr } = await supabase
    .from('alert_rules')
    .select('*')
    .eq('enabled', true)

  if (rulesErr || !rules?.length) {
    console.log('No active alert rules')
    return
  }

  // Get unique stock codes
  const codes = [...new Set(rules.map((r) => r.stock_code))]
  const tencentUrl = buildTencentUrl(codes)
  const res = await fetch(tencentUrl)
  const text = await res.text()
  const quotes = parseTencentResponse(text)

  const quoteMap = {}
  for (const q of quotes) {
    quoteMap[q.code] = q
  }

  // Get alert state for dedup
  const { data: states } = await supabase
    .from('alert_state')
    .select('*')

  const stateMap = {}
  for (const s of (states || [])) {
    stateMap[`${s.stock_code}:${s.alert_type}`] = s
  }

  const today = new Date().toISOString().slice(0, 10)

  for (const rule of rules) {
    const q = quoteMap[rule.stock_code]
    if (!q) continue

    const stateKey = `${rule.stock_code}:${rule.alert_type}`
    const state = stateMap[stateKey]

    // Check if already fired today (for daily-reset types)
    if (state) {
      const dailyTypes = ['limit_up', 'limit_down', 'volume_spike']
      if (dailyTypes.includes(rule.alert_type) && state.daily_reset_at === today) {
        continue // Already fired today
      }
      // price_target is one-shot — if ever fired, skip
      if (rule.alert_type === 'price_target' && state.last_fired_at) {
        continue
      }
    }

    const triggered = evaluateAlert(rule, q)
    if (!triggered) continue

    // Build elderly-friendly message
    const msg = buildAlertMessage(rule, q)
    await sendPush(msg.title, msg.content)

    // Update alert state
    await supabase.from('alert_state').upsert({
      stock_code: rule.stock_code,
      alert_type: rule.alert_type,
      last_fired_at: new Date().toISOString(),
      daily_reset_at: today,
    })

    // For price_target: disable after firing (one-shot)
    if (rule.alert_type === 'price_target') {
      await supabase
        .from('alert_rules')
        .update({ enabled: false, triggered_at: new Date().toISOString() })
        .eq('id', rule.id)
    }
  }
}

function evaluateAlert(rule, quote) {
  switch (rule.alert_type) {
    case 'price_target':
      if (rule.direction === 'above') return quote.price >= rule.threshold
      return quote.price <= rule.threshold

    case 'limit_up':
      return quote.change_pct >= 9.8

    case 'limit_down':
      return quote.change_pct <= -9.8

    case 'volume_spike':
      // volume_spike threshold = multiplier (e.g. 3 = 3x average)
      // Simplified: flag if turnover rate > threshold %
      return quote.turnover_rate >= (rule.threshold || 3)

    default:
      return false
  }
}

function buildAlertMessage(rule, quote) {
  const name = rule.stock_name || rule.stock_code
  const price = quote.price.toFixed(2)
  const change = (quote.change_pct > 0 ? '+' : '') + quote.change_pct.toFixed(2)

  const typeLabels = {
    price_target: '目标价提醒',
    limit_up: '涨停提醒',
    limit_down: '跌停提醒',
    volume_spike: '量能异动',
  }

  const title = `${typeLabels[rule.alert_type]} · ${name}`

  let content = `${name}(${rule.stock_code})\n`
  content += `现价: ¥${price}  涨跌: ${change}%\n`

  if (rule.alert_type === 'price_target') {
    content += `已${rule.direction === 'above' ? '突破' : '跌破'}目标价 ¥${rule.threshold}\n`
  }

  content += '⚠️ 仅供参考，不构成投资建议'

  return { title, content }
}

export const config = {
  schedule: '* 1-3,5-7 * * 1-5',
}
