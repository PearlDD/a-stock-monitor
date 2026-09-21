import { getSupabase } from './shared/supabase.js'
import { jsonResponse, handleOptions } from './shared/cors.js'
import { requireUser } from './shared/auth.js'
import { normalizeStockCode } from './shared/validation.js'

export default async (req, context) => {
  if (req.method === 'OPTIONS') return handleOptions(req)

  const auth = await requireUser(req)
  if (auth.response) return auth.response
  const userId = auth.user.id

  const supabase = getSupabase()
  const url = new URL(req.url)
  const pathParts = url.pathname.replace(/^\/api\//, '').split('/').filter(Boolean)
  // pathParts: ["watchlist"] or ["watchlist", "<code>"]

  try {
    if (req.method === 'GET') {
      const { data, error } = await supabase
        .from('watchlist')
        .select('*')
        .eq('user_id', userId)
        .order('created_at', { ascending: true })
      if (error) throw error
      return jsonResponse({ stocks: data })
    }

    if (req.method === 'POST') {
      const body = await req.json()
      const { code, name, market, sector } = body
      const normalizedCode = normalizeStockCode(code)
      if (!normalizedCode) return jsonResponse({ error: '请输入有效的 A 股代码或美股代码（如 AAPL）' }, 400, req)
      const { error } = await supabase
        .from('watchlist')
        .upsert({ user_id: userId, code: normalizedCode, name: String(name || normalizedCode).slice(0, 60), market, sector }, { onConflict: 'user_id,code' })
      if (error) throw error
      return jsonResponse({ success: true })
    }

    if (req.method === 'DELETE') {
      const code = normalizeStockCode(pathParts[1])
      if (!code) return jsonResponse({ error: '股票代码无效' }, 400, req)
      const { error } = await supabase
        .from('watchlist')
        .delete()
        .eq('user_id', userId)
        .eq('code', code)
      if (error) throw error
      return jsonResponse({ success: true })
    }

    return jsonResponse({ error: 'Method not allowed' }, 405)
  } catch (err) {
    return jsonResponse({ error: err.message }, 500)
  }
}

export const config = {
  path: ['/api/watchlist', '/api/watchlist/:code'],
}
