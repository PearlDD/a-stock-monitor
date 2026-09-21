import { getSupabase } from './shared/supabase.js'
import { jsonResponse, handleOptions } from './shared/cors.js'
import { requireUser } from './shared/auth.js'
import { encryptToken, getUserPushToken } from './shared/push-settings.js'
import { sendPush } from './shared/pushplus.js'

export default async (req) => {
  if (req.method === 'OPTIONS') return handleOptions(req)
  const auth = await requireUser(req)
  if (auth.response) return auth.response
  const userId = auth.user.id
  const path = new URL(req.url).pathname
  try {
    if (path.endsWith('/test-push') && req.method === 'POST') return testPush(userId, req)
    if (path.endsWith('/push-quota') && req.method === 'GET') return getPushQuota(userId, req)
    if (req.method === 'GET') {
      const { data, error } = await getSupabase().from('push_settings').select('user_id').eq('user_id', userId).maybeSingle()
      if (error) throw error
      return jsonResponse({ pushplus_token_set: Boolean(data), timezone: 'Asia/Shanghai' }, 200, req)
    }
    if (req.method === 'POST') {
      const token = String((await req.json()).pushplus_token || '').trim()
      if (token.length < 16 || token.length > 256) return jsonResponse({ error: 'PushPlus Token 格式无效' }, 400, req)
      const { error } = await getSupabase().from('push_settings').upsert({ user_id: userId, ...encryptToken(token), updated_at: new Date().toISOString() })
      if (error) throw error
      return jsonResponse({ success: true }, 200, req)
    }
    return jsonResponse({ error: 'Method not allowed' }, 405, req)
  } catch (err) {
    console.error('settings failed', err)
    return jsonResponse({ error: '设置操作失败' }, 500, req)
  }
}

async function testPush(userId, req) {
  const token = await getUserPushToken(userId)
  if (!token) return jsonResponse({ error: '请先保存 PushPlus Token' }, 400, req)
  const result = await sendPush('测试推送', '🔔 A股监控系统推送测试成功！\n系统运行正常。', { token, userId })
  return result.success ? jsonResponse({ success: true }, 200, req) : jsonResponse({ error: 'PushPlus 拒绝了该请求' }, 502, req)
}

async function getPushQuota(userId, req) {
  const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Shanghai' }).format(new Date())
  const { count, error } = await getSupabase().from('push_history').select('*', { count: 'exact', head: true }).eq('user_id', userId).gte('sent_at', `${today}T00:00:00+08:00`)
  if (error) throw error
  const used = count || 0
  return jsonResponse({ used, limit: 180, remaining: Math.max(0, 180 - used) }, 200, req)
}

export const config = { path: ['/api/settings', '/api/settings/test-push', '/api/test-push', '/api/push-quota'] }
