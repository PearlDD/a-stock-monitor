const ALERT_TYPES = new Set(['price_target', 'limit_up', 'limit_down', 'volume_spike'])
const DIRECTIONS = new Set(['above', 'below'])

export function normalizeStockCode(value) {
  let code = String(value || '').trim().toUpperCase()
  // A-share inputs may be entered as sh600519, 600519.SH, etc.
  code = code.replace(/^(SH|SZ)(?=\d{6}$)/, '').replace(/\.(SH|SZ)$/i, '')
  if (/^\d{6}$/.test(code)) return code

  // Tencent identifies US listings as usAAPL and search results as aapl.oq.
  // Store the portable ticker (AAPL), not a provider-specific exchange suffix.
  code = code.replace(/^US(?=[A-Z])/, '').replace(/\.(OQ|N|NYSE|NASDAQ)$/i, '')
  return /^[A-Z][A-Z0-9.-]{0,9}$/.test(code) ? code : null
}

export function stockMarket(code) {
  return /^\d{6}$/.test(code) ? 'CN' : 'US'
}

export function parseCodes(value, max = 50) {
  const codes = [...new Set(String(value || '').split(',').map(normalizeStockCode).filter(Boolean))]
  if (!codes.length || codes.length > max) return null
  return codes
}

export function validateAlert(body) {
  const stock_code = normalizeStockCode(body.stock_code)
  const alert_type = String(body.alert_type || '')
  const threshold = Number(body.threshold)
  const direction = String(body.direction || 'above')
  if (!stock_code || !ALERT_TYPES.has(alert_type) || !DIRECTIONS.has(direction)) return null
  if (alert_type === 'price_target' && (!Number.isFinite(threshold) || threshold <= 0)) return null
  if (alert_type === 'volume_spike' && (!Number.isFinite(threshold) || threshold <= 0 || threshold > 100)) return null
  return { stock_code, alert_type, threshold: Number.isFinite(threshold) ? threshold : 0, direction,
    stock_name: String(body.stock_name || stock_code).trim().slice(0, 60) }
}
