import { getSupabase } from './shared/supabase.js'

/**
 * Scheduled: health check at 01:00 UTC (= 09:00 CST, before market open).
 * Verifies Supabase connectivity and logs status.
 */
export default async () => {
  const supabase = getSupabase()

  try {
    // Test Supabase connectivity
    const { count, error } = await supabase
      .from('watchlist')
      .select('*', { count: 'exact', head: true })

    if (error) {
      console.error('Health check failed — Supabase error:', error.message)
      return
    }

    console.log(`Health check OK — watchlist has ${count} stocks`)

    // Clean up old alert_state entries (daily reset)
    const yesterday = new Date()
    yesterday.setDate(yesterday.getDate() - 1)
    const yesterdayStr = yesterday.toISOString().slice(0, 10)

    await supabase
      .from('alert_state')
      .delete()
      .lt('daily_reset_at', yesterdayStr)

    console.log('Cleaned up stale alert_state entries')
  } catch (err) {
    console.error('Health check error:', err.message)
  }
}

export const config = {
  schedule: '0 1 * * *',
}
