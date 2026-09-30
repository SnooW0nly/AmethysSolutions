import { NextRequest, NextResponse } from 'next/server'
import crypto from 'crypto'

const SIGNED_PATHS = [
  '/v1/withdraw/create',
  '/v1/withdraw/crypto',
  '/v1/transfer/internal',
  '/v1/payment/send',
]

function generateSignature(secret: string, timestamp: string, method: string, path: string, body: string) {
  let parsedBody: unknown = {}
  try {
    parsedBody = body ? JSON.parse(body) : {}
  } catch {
    parsedBody = {}
  }
  const payload = `${timestamp}:${method.toUpperCase()}:${path}:${JSON.stringify(parsedBody)}`
  return crypto.createHmac('sha256', secret).update(payload).digest('hex')
}

async function proxy(
  req: NextRequest,
  pathParts: string[],
  method: string
): Promise<NextResponse> {
  const BACKEND_URL = process.env.BACKEND_URL
  const FRONTEND_API_KEY = process.env.FRONTEND_API_KEY
  const REQUEST_SIGNING_SECRET = process.env.REQUEST_SIGNING_SECRET

  if (!BACKEND_URL) {
    console.error('[PROXY] BACKEND_URL não configurado no .env')
    return NextResponse.json(
      { success: false, error: 'Configuração interna inválida.' },
      { status: 500 }
    )
  }

  if (!FRONTEND_API_KEY) {
    console.warn('[PROXY] ⚠️ FRONTEND_API_KEY não configurado no .env')
  }

  try {
    const path = pathParts.join('/')
    const search = req.nextUrl.search
    const url = `${BACKEND_URL}/api/${path}${search}`

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }

    if (FRONTEND_API_KEY) {
      headers['X-API-Key'] = FRONTEND_API_KEY
    }

    const auth = req.headers.get('authorization')
    if (auth) {
      headers['Authorization'] = auth
    }

    const cookie = req.headers.get('cookie')
    if (cookie) {
      headers['Cookie'] = cookie
    }

    const forwardedFor = req.headers.get('x-forwarded-for')
    const realIp = req.headers.get('x-real-ip')
    if (forwardedFor) {
      headers['X-Forwarded-For'] = forwardedFor
    } else if (realIp) {
      headers['X-Forwarded-For'] = realIp
    }

    const userAgent = req.headers.get('user-agent')
    if (userAgent) {
      headers['User-Agent'] = userAgent
    }

    const origin = req.headers.get('origin')
    if (origin) {
      headers['Origin'] = origin
    } else {
      const frontendUrl = process.env.FRONTEND_URL || 'https://www.amethys.lat'
      headers['Origin'] = frontendUrl
    }

    const referer = req.headers.get('referer')
    if (referer) {
      headers['Referer'] = referer
    }

    let body: string | undefined
    if (method !== 'GET' && method !== 'HEAD') {
      body = await req.text()
    }

    // Assinar requisições sensíveis no servidor (secret nunca vai ao browser)
    const backendPath = `/api/${path}`
    const needsSignature =
      REQUEST_SIGNING_SECRET &&
      ['POST', 'PUT', 'DELETE'].includes(method) &&
      SIGNED_PATHS.some(p => backendPath.startsWith(`/api${p}`))

    if (needsSignature) {
      const timestamp = Date.now().toString()
      const signature = generateSignature(REQUEST_SIGNING_SECRET, timestamp, method, backendPath, body || '')
      headers['X-Request-Timestamp'] = timestamp
      headers['X-Request-Signature'] = signature
    }

    const backendResponse = await fetch(url, {
      method,
      headers,
      body,
    })

    const responseText = await backendResponse.text()

    const responseHeaders: Record<string, string> = {
      'Content-Type': backendResponse.headers.get('content-type') || 'application/json',
    }

    const setCookie = backendResponse.headers.get('set-cookie')
    if (setCookie) {
      responseHeaders['Set-Cookie'] = setCookie
    }

    return new NextResponse(responseText, {
      status: backendResponse.status,
      headers: responseHeaders,
    })
  } catch (error) {
    console.error('[PROXY] Erro ao conectar com o backend:', error)
    return NextResponse.json(
      { success: false, error: 'Servidor indisponível. Tente novamente em instantes.' },
      { status: 503 }
    )
  }
}

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params
  return proxy(req, path, 'GET')
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params
  return proxy(req, path, 'POST')
}

export async function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params
  return proxy(req, path, 'PUT')
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params
  return proxy(req, path, 'DELETE')
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params
  return proxy(req, path, 'PATCH')
}