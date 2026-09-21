export function corsHeaders(request) {
  const origin = request?.headers?.get('origin')
  const allowedOrigin = process.env.ALLOWED_ORIGIN
  return {
    ...(allowedOrigin && origin === allowedOrigin ? { 'Access-Control-Allow-Origin': allowedOrigin, Vary: 'Origin' } : {}),
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  }
}

export function jsonResponse(data, status = 200, request) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...corsHeaders(request), 'Content-Type': 'application/json' },
  })
}

export function handleOptions(request) {
  return new Response(null, { status: 204, headers: corsHeaders(request) })
}
