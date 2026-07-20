import { getSupabase } from './shared/supabase.js'
import { jsonResponse, handleOptions } from './shared/cors.js'

export default async (req) => {
  if (req.method === 'OPTIONS') return handleOptions()

  const url = new URL(req.url)
  const path = url.pathname

  try {
    // POST /api/test-push — alias for /api/settings/test-push
    if (path.endsWith('/test-push') && req.method === 'POST') {
      return await testPush()
    }

    // GET /api/push-quota
    if (path.endsWith('/push-quota') && req.method === 'GET') {
      return await getPushQuota()
    }

    // GET /api/settings
    if (req.method === 'GET') {
      const hasToken = !!process.env.PUSHPLUS_TOKEN
      return jsonResponse({
        pushplus_token_set: hasToken,
        timezone: 'Asia/Shanghai',
      })
    }

    // POST /api/settings
    if (req.method === 'POST') {
      // In serverless, PushPlus token is set via env vars (Netlify dashboard).
      // We can't persist it server-side, but we acknowledge the request.
      return jsonResponse({
        success: true,
        message: 'PushPlus Token 请在 Netlify 环境变量中配置',
      })
    }

    return jsonResponse({ error: 'Method not allowed' }, 405)
  } catch (err) {
    return jsonResponse({ error: err.message }, 500)
  }
}

async function testPush() {
  const token = process.env.PUSHPLUS_TOKEN
  if (!token) {
    return jsonResponse({ error: 'PushPlus Token 未配置' }, 400)
  }

  const body = JSON.stringify({
    token,
    title: '测试推送',
    content: '🔔 A股监控系统推送测试成功！\n系统运行正常。',
    topic: '',
  })

  const res = await fetch('http://www.pushplus.plus/send', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
  })
  const result = await res.json()

  // Log to push_history
  const supabase = getSupabase()
  await supabase.from('push_history').insert({
    title: '测试推送',
    content: '推送测试',
    status: result.code === 200 ? 'success' : 'failed',
  })

  if (result.code === 200) {
    return jsonResponse({ success: true, message: '测试消息已发送' })
  }
  return jsonResponse({ error: result.msg || '发送失败' }, 500)
}

async function getPushQuota() {
  const supabase = getSupabase()
  const today = new Date().toISOString().slice(0, 10)

  const { count } = await supabase
    .from('push_history')
    .select('*', { count: 'exact', head: true })
    .gte('sent_at', `${today}T00:00:00+08:00`)

  const used = count || 0
  const limit = 180
  return jsonResponse({ used, limit, remaining: limit - used })
}

export const config = {
  path: ['/api/settings', '/api/settings/test-push', '/api/test-push', '/api/push-quota'],
}
