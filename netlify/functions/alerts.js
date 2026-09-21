import { getSupabase } from './shared/supabase.js'
import { jsonResponse, handleOptions } from './shared/cors.js'
import { requireUser } from './shared/auth.js'
import { validateAlert } from './shared/validation.js'
import { buildTencentUrl, fetchTencentGBK, parseTencentResponse } from './shared/tencent.js'

export default async (req, context) => {
  if (req.method === 'OPTIONS') return handleOptions(req)
  const auth = await requireUser(req)
  if (auth.response) return auth.response
  const userId = auth.user.id

  const supabase = getSupabase()
  const url = new URL(req.url)
  const pathParts = url.pathname.replace(/^\/api\//, '').split('/').filter(Boolean)
  // pathParts: ["alerts"] or ["alerts", "<id>"]
  const alertId = pathParts[1] ? parseInt(pathParts[1], 10) : null

  try {
    if (req.method === 'GET') {
      const { data, error } = await supabase
        .from('alert_rules')
        .select('*')
        .eq('user_id', userId)
        .order('created_at', { ascending: false })
      if (error) throw error
      return jsonResponse({ alerts: data })
    }

    if (req.method === 'POST') {
      const body = await req.json()
      const rule = validateAlert(body)
      if (!rule) return jsonResponse({ error: '提醒参数无效：目标价和量能阈值必须为正数' }, 400, req)
      // Do not accept a typo such as APPL and create a rule that can never fire.
      const quoteText = await fetchTencentGBK(buildTencentUrl([rule.stock_code]))
      const quote = parseTencentResponse(quoteText).find((item) => item.code === rule.stock_code)
      if (!quote) return jsonResponse({ error: `未找到股票代码 ${rule.stock_code}，请使用搜索结果中的代码` }, 404, req)
      rule.stock_name = quote.name || rule.stock_name
      const { data, error } = await supabase
        .from('alert_rules')
        .insert({ ...rule, user_id: userId, enabled: true })
        .select()
      if (error) throw error
      return jsonResponse({ alert: data[0] })
    }

    if (req.method === 'PUT') {
      if (!alertId) return jsonResponse({ error: '需要提醒ID' }, 400)
      const body = await req.json()
      const allowed = {}
      if (typeof body.enabled === 'boolean') allowed.enabled = body.enabled
      if (body.threshold !== undefined || body.direction !== undefined) {
        const existing = await supabase.from('alert_rules').select('*').eq('id', alertId).eq('user_id', userId).single()
        const rule = validateAlert({ ...existing.data, ...body })
        if (!rule) return jsonResponse({ error: '提醒参数无效' }, 400, req)
        Object.assign(allowed, rule)
      }
      if (!Object.keys(allowed).length) return jsonResponse({ error: '没有可更新的字段' }, 400, req)
      const { error } = await supabase
        .from('alert_rules')
        .update(allowed)
        .eq('id', alertId)
        .eq('user_id', userId)
      if (error) throw error
      return jsonResponse({ success: true })
    }

    if (req.method === 'DELETE') {
      if (!alertId) return jsonResponse({ error: '需要提醒ID' }, 400)
      const { error } = await supabase
        .from('alert_rules')
        .delete()
        .eq('id', alertId)
        .eq('user_id', userId)
      if (error) throw error
      return jsonResponse({ success: true })
    }

    return jsonResponse({ error: 'Method not allowed' }, 405)
  } catch (err) {
    return jsonResponse({ error: err.message }, 500)
  }
}

export const config = {
  path: ['/api/alerts', '/api/alerts/:id'],
}
