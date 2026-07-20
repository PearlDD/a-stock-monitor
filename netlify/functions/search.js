import { fetchTencentGBK } from './shared/tencent.js'
import { jsonResponse, handleOptions } from './shared/cors.js'

/**
 * Stock search — queries Tencent Finance smartbox API.
 * URL: https://smartbox.gtimg.cn/s3/?q=<query>&t=gp
 */
export default async (req) => {
  if (req.method === 'OPTIONS') return handleOptions()

  const url = new URL(req.url)
  const q = url.searchParams.get('q')

  if (!q) {
    return jsonResponse({ results: [] })
  }

  try {
    const searchUrl = `https://smartbox.gtimg.cn/s3/?q=${encodeURIComponent(q)}&t=gp`
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
        return {
          code: parts[1],
          name: parts[3],
          market: parts[0] === 'sh' ? 'SH' : 'SZ',
        }
      })
      .slice(0, 10)

    return jsonResponse({ results })
  } catch (err) {
    return jsonResponse({ error: err.message }, 500)
  }
}

export const config = {
  path: '/api/search',
}
