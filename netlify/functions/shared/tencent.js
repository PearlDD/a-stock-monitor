import iconv from 'iconv-lite'

/**
 * Tencent Finance API (qt.gtimg.cn) quote parser.
 *
 * Response format: v_sh600519="1~贵州茅台~600519~1849.00~1833.33~..."
 * Fields (0-indexed, split by ~):
 *  1: name, 2: code, 3: current price, 4: prev close, 5: open,
 *  6: volume (lots), 30: date, 31: high, 32: low,
 *  36: turnover rate, 37: PE, 38: amount (万), 44: total market cap (亿)
 *
 * IMPORTANT: Tencent API returns GBK-encoded text.
 * Use fetchTencentGBK() instead of fetch().text() to get proper UTF-8.
 */

/**
 * Fetch a Tencent API URL and decode the GBK response to UTF-8 string.
 */
export async function fetchTencentGBK(url, { retries = 2, timeoutMs = 8000 } = {}) {
  let lastError
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    try {
      const res = await fetch(url, { signal: controller.signal })
      if (!res.ok) throw new Error(`行情服务返回 HTTP ${res.status}`)
      const buffer = await res.arrayBuffer()
      const text = iconv.decode(Buffer.from(buffer), 'gbk')
      if (!text.trim()) throw new Error('行情服务返回空数据')
      return text
    } catch (error) {
      lastError = error
      if (attempt < retries) await new Promise((resolve) => setTimeout(resolve, 250 * (2 ** attempt)))
    } finally {
      clearTimeout(timer)
    }
  }
  throw new Error(`行情服务不可用: ${lastError?.message || 'unknown error'}`)
}

export function buildTencentUrl(codes) {
  const mapped = codes.map((code) => {
    const c = String(code).toUpperCase().replace(/\.(SH|SZ)$/i, '')
    if (!/^\d{6}$/.test(c)) return `us${c}`
    if (c.startsWith('6') || c.startsWith('5') || c.startsWith('9')) {
      return `sh${c}`
    }
    return `sz${c}`
  })
  return `https://qt.gtimg.cn/q=${mapped.join(',')}`
}

export function parseTencentResponse(text) {
  const quotes = []
  const lines = text.split(';').filter((l) => l.includes('~'))

  for (const line of lines) {
    const match = line.match(/"([^"]+)"/)
    if (!match) continue

    const fields = match[1].split('~')
    if (fields.length < 45) continue

    const price = Number.parseFloat(fields[3])
    const prevClose = Number.parseFloat(fields[4])
    // A zero/invalid price is normally a suspended or malformed response, never an alert.
    if (!Number.isFinite(price) || price <= 0 || !Number.isFinite(prevClose) || prevClose <= 0) continue
    const changePct = prevClose ? ((price - prevClose) / prevClose) * 100 : 0

    const providerCode = line.match(/^v_([^=]+)=/)?.[1] || ''
    const isUS = providerCode.toLowerCase().startsWith('us')
    const code = isUS ? fields[2].split('.')[0].toUpperCase() : fields[2]
    quotes.push({
      code,
      name: fields[1],
      price,
      prev_close: prevClose,
      open: parseFloat(fields[5]) || 0,
      high: parseFloat(isUS ? fields[33] : fields[31]) || 0,
      low: parseFloat(isUS ? fields[34] : fields[32]) || 0,
      volume: (parseFloat(fields[6]) || 0) * (isUS ? 1 : 100),
      amount: (parseFloat(isUS ? fields[37] : fields[38]) || 0) * (isUS ? 1 : 10000),
      change_pct: parseFloat(changePct.toFixed(2)),
      turnover_rate: parseFloat(isUS ? fields[38] : fields[36]) || 0,
      pe_ratio: parseFloat(isUS ? fields[39] : fields[37]) || 0,
      market_cap: parseFloat(fields[44]) * 1e8 || 0,
      timestamp: fields[30] || '',
      market: isUS ? 'US' : (providerCode.startsWith('sh') ? 'SH' : 'SZ'),
      currency: isUS ? 'USD' : 'CNY',
    })
  }
  return quotes
}
