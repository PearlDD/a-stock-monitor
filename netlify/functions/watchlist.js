import { getSupabase } from './shared/supabase.js'
import { jsonResponse, handleOptions } from './shared/cors.js'

export default async (req, context) => {
  if (req.method === 'OPTIONS') return handleOptions()

  const supabase = getSupabase()
  const url = new URL(req.url)
  const pathParts = url.pathname.replace(/^\/api\//, '').split('/').filter(Boolean)
  // pathParts: ["watchlist"] or ["watchlist", "<code>"]

  try {
    if (req.method === 'GET') {
      const { data, error } = await supabase
        .from('watchlist')
        .select('*')
        .order('created_at', { ascending: true })
      if (error) throw error
      return jsonResponse({ stocks: data })
    }

    if (req.method === 'POST') {
      const body = await req.json()
      const { code, name, market, sector } = body
      if (!code) return jsonResponse({ error: '股票代码不能为空' }, 400)
      const { error } = await supabase
        .from('watchlist')
        .upsert({ code, name: name || code, market, sector })
      if (error) throw error
      return jsonResponse({ success: true })
    }

    if (req.method === 'DELETE') {
      const code = pathParts[1]
      if (!code) return jsonResponse({ error: '股票代码不能为空' }, 400)
      const { error } = await supabase
        .from('watchlist')
        .delete()
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
