import crypto from 'node:crypto'
import { getSupabase } from './supabase.js'

function key() {
  const value = process.env.APP_ENCRYPTION_KEY
  if (!value) throw new Error('APP_ENCRYPTION_KEY 未配置')
  const decoded = Buffer.from(value, 'base64')
  if (decoded.length !== 32) throw new Error('APP_ENCRYPTION_KEY 必须是 base64 编码的 32 字节密钥')
  return decoded
}

export function encryptToken(token) {
  const iv = crypto.randomBytes(12)
  const cipher = crypto.createCipheriv('aes-256-gcm', key(), iv)
  const ciphertext = Buffer.concat([cipher.update(token, 'utf8'), cipher.final()])
  return { token_ciphertext: ciphertext.toString('base64'), token_iv: iv.toString('base64'), token_tag: cipher.getAuthTag().toString('base64') }
}

export function decryptToken(row) {
  const decipher = crypto.createDecipheriv('aes-256-gcm', key(), Buffer.from(row.token_iv, 'base64'))
  decipher.setAuthTag(Buffer.from(row.token_tag, 'base64'))
  return Buffer.concat([decipher.update(Buffer.from(row.token_ciphertext, 'base64')), decipher.final()]).toString('utf8')
}

export async function getUserPushToken(userId) {
  const { data, error } = await getSupabase().from('push_settings').select('*').eq('user_id', userId).maybeSingle()
  if (error) throw error
  return data ? decryptToken(data) : null
}
