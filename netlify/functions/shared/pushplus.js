import { getSupabase } from './supabase.js'

/**
 * Send a PushPlus notification and log to push_history.
 * Message format: 3-4 lines, elderly-friendly, with disclaimer.
 */
export async function sendPush(title, content, { token, userId } = {}) {
  if (!token) {
    console.warn('PushPlus token not configured, skipping push')
    return { success: false, reason: 'no_token' }
  }

  // Check daily quota
  const supabase = getSupabase()
  const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Shanghai' }).format(new Date())
  const { count } = await supabase
    .from('push_history')
    .select('*', { count: 'exact', head: true })
    .gte('sent_at', `${today}T00:00:00+08:00`)
    .eq('user_id', userId)

  if ((count || 0) >= 180) {
    console.warn('Daily push quota exceeded (180)')
    return { success: false, reason: 'quota_exceeded' }
  }

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 10000)
  let result
  try {
    const res = await fetch('https://www.pushplus.plus/send', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token, title, content, topic: '' }), signal: controller.signal })
    if (!res.ok) throw new Error(`PushPlus 返回 HTTP ${res.status}`)
    result = await res.json()
  } catch (error) {
    await supabase.from('push_history').insert({ user_id: userId, title, content: '推送请求失败', status: 'failed' })
    throw error
  } finally { clearTimeout(timer) }
  const success = result.code === 200

  await supabase.from('push_history').insert({
    user_id: userId, title,
    content,
    status: success ? 'success' : 'failed',
  })

  return { success, result }
}
