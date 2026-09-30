// lib/requestSigning.ts

const SIGNING_SECRET = process.env.NEXT_PUBLIC_REQUEST_SIGNING_SECRET || ''

async function hmacSha256(secret: string, message: string): Promise<string> {
  const enc = new TextEncoder()
  const key = await crypto.subtle.importKey(
    'raw',
    enc.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  )
  const signature = await crypto.subtle.sign('HMAC', key, enc.encode(message))
  return Array.from(new Uint8Array(signature))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('')
}

export async function signedHeaders(
  method: string,
  path: string,
  body: unknown
): Promise<Record<string, string>> {
  if (!SIGNING_SECRET) return {}

  const timestamp = Date.now().toString()
  const payload = `${timestamp}:${method.toUpperCase()}:${path}:${JSON.stringify(body || {})}`
  const signature = await hmacSha256(SIGNING_SECRET, payload)

  return {
    'X-Request-Timestamp': timestamp,
    'X-Request-Signature': signature,
  }
}