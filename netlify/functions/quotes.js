import { buildTencentUrl, parseTencentResponse, fetchTencentGBK } from './shared/tencent.js'
import { jsonResponse, handleOptions } from './shared/cors.js'
import { requireUser } from './shared/auth.js'
import { parseCodes } from './shared/validation.js'

export default async (req) => {
  if (req.method === 'OPTIONS') return handleOptions(req)
  const auth = await requireUser(req)
  if (auth.response) return auth.response

  const url = new URL(req.url)
  const codesParam = url.searchParams.get('codes')

  if (!codesParam) {
    return jsonResponse({ error: '需要codes参数' }, 400)
  }

  const codes = parseCodes(codesParam)
  if (!codes) {
    return jsonResponse({ error: '股票代码必须为 1–50 个有效 A 股或美股代码' }, 400, req)
  }

  try {
    const tencentUrl = buildTencentUrl(codes)
    const text = await fetchTencentGBK(tencentUrl)
    const quotes = parseTencentResponse(text)

    return jsonResponse({ quotes, market_status: 'live' })
  } catch (err) {
    return jsonResponse({ error: err.message }, 500)
  }
}

export const config = {
  path: '/api/stocks/quotes',
}
