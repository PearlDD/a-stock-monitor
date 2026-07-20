import { buildTencentUrl, parseTencentResponse, fetchTencentGBK } from './shared/tencent.js'
import { jsonResponse, handleOptions } from './shared/cors.js'

export default async (req) => {
  if (req.method === 'OPTIONS') return handleOptions()

  const url = new URL(req.url)
  const codesParam = url.searchParams.get('codes')

  if (!codesParam) {
    return jsonResponse({ error: '需要codes参数' }, 400)
  }

  const codes = codesParam.split(',').map((c) => c.trim()).filter(Boolean)
  if (!codes.length) {
    return jsonResponse({ error: '股票代码不能为空' }, 400)
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
