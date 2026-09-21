/**
 * Check if we're currently in A-share trading hours.
 * Trading: 9:30-11:30, 13:00-15:00 Asia/Shanghai, Mon-Fri
 */
export function isTradingHours(now = new Date()) {
  const formatter = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Shanghai',
    hour: 'numeric',
    minute: 'numeric',
    hour12: false,
    weekday: 'short',
  })

  const parts = formatter.formatToParts(now)
  const weekday = parts.find((p) => p.type === 'weekday')?.value
  const hour = parseInt(parts.find((p) => p.type === 'hour')?.value || '0', 10)
  const minute = parseInt(parts.find((p) => p.type === 'minute')?.value || '0', 10)

  // Weekend check
  if (weekday === 'Sat' || weekday === 'Sun') return false

  const time = hour * 60 + minute
  const morningOpen = 9 * 60 + 30
  const morningClose = 11 * 60 + 30
  const afternoonOpen = 13 * 60
  const afternoonClose = 15 * 60

  return (time >= morningOpen && time <= morningClose) ||
    (time >= afternoonOpen && time <= afternoonClose)
}

/**
 * Regular-hours guard for supported markets. Exchange holidays are handled by
 * the provider returning no fresh quote; this guard prevents needless polling
 * overnight and avoids evaluating stale US prices during the China session.
 */
export function isMarketTradingHours(code, now = new Date()) {
  if (/^\d{6}$/.test(code)) return isTradingHours(now)

  const formatter = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/New_York', hour: 'numeric', minute: 'numeric', hour12: false, weekday: 'short',
  })
  const parts = formatter.formatToParts(now)
  const weekday = parts.find((part) => part.type === 'weekday')?.value
  if (weekday === 'Sat' || weekday === 'Sun') return false
  const hour = parseInt(parts.find((part) => part.type === 'hour')?.value || '0', 10)
  const minute = parseInt(parts.find((part) => part.type === 'minute')?.value || '0', 10)
  const time = hour * 60 + minute
  return time >= 9 * 60 + 30 && time <= 16 * 60
}
