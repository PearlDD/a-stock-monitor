/**
 * Tencent Finance API (qt.gtimg.cn) quote parser.
 *
 * Response format: v_sh600519="1~贵州茅台~600519~1849.00~1833.33~..."
 * Fields (0-indexed, split by ~):
 *  1: name, 2: code, 3: current price, 4: prev close, 5: open,
 *  6: volume (lots), 30: date, 31: high, 32: low,
 *  36: turnover rate, 37: PE, 38: amount (万), 44: total market cap (亿)
 */

export function buildTencentUrl(codes) {
  const mapped = codes.map((code) => {
    const c = code.replace(/\.(SH|SZ)$/i, '')
    if (c.startsWith('6') || c.startsWith('5') || c.startsWith('9')) {
      return `sh${c}`
    }
    return `sz${c}`
  })
  return `http://qt.gtimg.cn/q=${mapped.join(',')}`
}

export function parseTencentResponse(text) {
  const quotes = []
  const lines = text.split(';').filter((l) => l.includes('~'))

  for (const line of lines) {
    const match = line.match(/"([^"]+)"/)
    if (!match) continue

    const fields = match[1].split('~')
    if (fields.length < 45) continue

    const price = parseFloat(fields[3]) || 0
    const prevClose = parseFloat(fields[4]) || 0
    const changePct = prevClose ? ((price - prevClose) / prevClose) * 100 : 0

    quotes.push({
      code: fields[2],
      name: fields[1],
      price,
      prev_close: prevClose,
      open: parseFloat(fields[5]) || 0,
      high: parseFloat(fields[31]) || 0,
      low: parseFloat(fields[32]) || 0,
      volume: parseFloat(fields[6]) * 100 || 0,
      amount: parseFloat(fields[38]) * 10000 || 0,
      change_pct: parseFloat(changePct.toFixed(2)),
      turnover_rate: parseFloat(fields[36]) || 0,
      pe_ratio: parseFloat(fields[37]) || 0,
      market_cap: parseFloat(fields[44]) * 1e8 || 0,
      timestamp: fields[30] || '',
    })
  }
  return quotes
}
