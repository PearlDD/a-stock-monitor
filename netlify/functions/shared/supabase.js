import { createClient } from '@supabase/supabase-js'

let client = null

export function getSupabase() {
  if (!client) {
    const url = process.env.SUPABASE_URL
    const key = process.env.SUPABASE_SERVICE_ROLE_KEY
    if (!url || !key) {
      throw new Error('Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY env vars')
    }
    client = createClient(url, key)
  }
  return client
}
