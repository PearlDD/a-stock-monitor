import test from 'node:test'
import assert from 'node:assert/strict'
import { parseCodes, validateAlert } from '../netlify/functions/shared/validation.js'
import { parseTencentResponse } from '../netlify/functions/shared/tencent.js'

test('only valid, bounded stock codes are accepted', () => {
  assert.deepEqual(parseCodes('600519, sz000001, AAPL, aapl.oq, @@@, 600519'), ['600519', '000001', 'AAPL'])
  assert.equal(parseCodes('@@@'), null)
  assert.equal(parseCodes(Array.from({ length: 51 }, (_, i) => String(600000 + i)).join(',')), null)
})

test('US Tencent quotes are normalized to portable tickers', () => {
  const fields = Array(50).fill('0')
  fields[1] = 'Apple'; fields[2] = 'AAPL.OQ'; fields[3] = '336.11'; fields[4] = '337.00'
  fields[5] = '337.91'; fields[6] = '28994141'; fields[33] = '338.49'; fields[34] = '332.53'
  const [quote] = parseTencentResponse(`v_usAAPL="${fields.join('~')}";`)
  assert.equal(quote.code, 'AAPL')
  assert.equal(quote.market, 'US')
  assert.equal(quote.currency, 'USD')
  assert.equal(quote.price, 336.11)
})

test('target alerts reject dangerous thresholds', () => {
  assert.equal(validateAlert({ stock_code: '600519', alert_type: 'price_target', threshold: 0, direction: 'above' }), null)
  assert.equal(validateAlert({ stock_code: '600519', alert_type: 'price_target', threshold: 1800, direction: 'above' }).stock_code, '600519')
})

test('malformed or zero Tencent prices are not emitted as quotes', () => {
  const fields = Array(45).fill('0')
  fields[1] = '测试'; fields[2] = '600519'; fields[3] = '0'; fields[4] = '100'
  assert.deepEqual(parseTencentResponse(`v_sh600519="${fields.join('~')}";`), [])
})
