import { getSupabase } from './shared/supabase.js'
import { jsonResponse, handleOptions } from './shared/cors.js'

export default async (req, context) => {
  if (req.method === 'OPTIONS') return handleOptions()

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
        .order('created_at', { ascending: false })
      if (error) throw error
      return jsonResponse({ alerts: data })
    }

    if (req.method === 'POST') {
      const body = await req.json()
      const { stock_code, stock_name, alert_type, threshold, direction } = body
      if (!stock_code || !alert_type) {
        return jsonResponse({ error: '股票代码和提醒类型不能为空' }, 400)
      }
      const { data, error } = await supabase
        .from('alert_rules')
        .insert({
          stock_code,
          stock_name: stock_name || stock_code,
          alert_type,
          threshold: threshold || 0,
          direction: direction || 'above',
          enabled: true,
        })
        .select()
      if (error) throw error
      return jsonResponse({ alert: data[0] })
    }

    if (req.method === 'PUT') {
      if (!alertId) return jsonResponse({ error: '需要提醒ID' }, 400)
      const body = await req.json()
      const { error } = await supabase
        .from('alert_rules')
        .update(body)
        .eq('id', alertId)
      if (error) throw error
      return jsonResponse({ success: true })
    }

    if (req.method === 'DELETE') {
      if (!alertId) return jsonResponse({ error: '需要提醒ID' }, 400)
      const { error } = await supabase
        .from('alert_rules')
        .delete()
        .eq('id', alertId)
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
