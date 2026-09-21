import { fetchTencentGBK } from './shared/tencent.js'
import { jsonResponse, handleOptions } from './shared/cors.js'
import { requireUser } from './shared/auth.js'

/**
 * Stock search — Tencent smartbox returns both Chinese and US listings with t=all.
 */
export default async (req) => {
  if (req.method === 'OPTIONS') return handleOptions(req)
  const auth = await requireUser(req)
  if (auth.response) return auth.response

  const url = new URL(req.url)
  const q = url.searchParams.get('q')?.trim().slice(0, 40)

  if (!q) {
    return jsonResponse({ results: [] })
  }

  try {
    const searchUrl = `https://smartbox.gtimg.cn/s3/?q=${encodeURIComponent(q)}&t=all`
    const text = await fetchTencentGBK(searchUrl)

    // Response format: v_hint="sh~600519~gp~贵州茅台~...^sz~000001~gp~平安银行~..."
    const match = text.match(/"([^"]*)"/)
    if (!match || !match[1]) {
      return jsonResponse({ results: [] })
    }

    const results = match[1]
      .split('^')
      .filter(Boolean)
      .map((item) => {
        const parts = item.split('~')
        const type = parts[0]?.toLowerCase()
        if (!['sh', 'sz', 'us'].includes(type) || !parts[1] || !parts[2]) return null
        return {
          code: type === 'us' ? parts[1].split('.')[0].toUpperCase() : parts[1],
          name: parts[2],
          market: type === 'us' ? 'US' : type.toUpperCase(),
        }
      })
      .filter(Boolean)
      .slice(0, 10)

    return jsonResponse({ results })
  } catch (err) {
    return jsonResponse({ error: err.message }, 500)
  }
}

export const config = {
  path: '/api/search',
}
