import { getSupabase } from './shared/supabase.js'
import { jsonResponse, handleOptions } from './shared/cors.js'
import { requireUser } from './shared/auth.js'

// Browser-visible reminders for signed-in users. Delivery rows are scoped via
// the rule owner, so one user can never read another user's alert history.
export default async (req) => {
  if (req.method === 'OPTIONS') return handleOptions(req)
  if (req.method !== 'GET') return jsonResponse({ error: 'Method not allowed' }, 405, req)
  const auth = await requireUser(req)
  if (auth.response) return auth.response

  try {
    const supabase = getSupabase()
    const { data: rules, error: rulesError } = await supabase
      .from('alert_rules')
      .select('id, stock_code, stock_name, alert_type, threshold, direction')
      .eq('user_id', auth.user.id)
    if (rulesError) throw rulesError
    if (!rules?.length) return jsonResponse({ notifications: [] }, 200, req)

    const ruleById = new Map(rules.map((rule) => [rule.id, rule]))
    const { data: deliveries, error: deliveryError } = await supabase
      .from('alert_deliveries')
      .select('id, alert_rule_id, trading_date, updated_at')
      .in('alert_rule_id', rules.map((rule) => rule.id))
      .eq('status', 'sent')
      .order('updated_at', { ascending: false })
      .limit(20)
    if (deliveryError) throw deliveryError

    const notifications = (deliveries || []).map((delivery) => ({
      id: delivery.id,
      trading_date: delivery.trading_date,
      triggered_at: delivery.updated_at,
      rule: ruleById.get(delivery.alert_rule_id),
    })).filter((item) => item.rule)
    return jsonResponse({ notifications }, 200, req)
  } catch (error) {
    console.error('alert notifications failed', error.message)
    return jsonResponse({ error: '获取网页提醒失败' }, 500, req)
  }
}

export const config = { path: '/api/alert-notifications' }
