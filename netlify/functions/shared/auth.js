import { getSupabase } from './supabase.js'
import { jsonResponse } from './cors.js'

export async function requireUser(request) {
  const header = request.headers.get('authorization') || ''
  const token = header.match(/^Bearer\s+(.+)$/i)?.[1]
  if (!token) return { response: jsonResponse({ error: '请先登录' }, 401, request) }

  const { data: { user }, error } = await getSupabase().auth.getUser(token)
  if (error || !user) return { response: jsonResponse({ error: '登录已失效，请重新登录' }, 401, request) }
  return { user }
}
