import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname.toLowerCase()
  const hostname = request.headers.get('host') || ''

  // Lista de arquivos estáticos que não devem cair na rota [affiliate]
  const staticFiles = ['favicon.ico', 'favicon.svg', 'robots.txt', 'sitemap.xml', 'manifest.json', 'icon.svg']
  const staticExtensions = ['.ico', '.svg', '.png', '.jpg', '.jpeg', '.json', '.txt', '.xml', '.webp', '.woff', '.woff2', '.ttf', '.eot']

  // Se for um arquivo estático, deixar o Next.js servir normalmente (não interceptar)
  const isStaticFile = staticFiles.some(file => pathname === `/${file}` || pathname.includes(`/${file}`)) || 
                       staticExtensions.some(ext => pathname.endsWith(ext))

  if (isStaticFile) {
    return NextResponse.next()
  }

  // Subdomínio docs.amethys.lat → rewrite para /docs/*
  const isDocsSubdomain = hostname.startsWith('docs.')

  if (isDocsSubdomain) {
    // Evita duplicar /docs se o pathname já vier com /docs (ex: docs.amethys.lat/docs/pagamentos/criar)
    const alreadyPrefixed = pathname.startsWith('/docs')
    const newPathname = alreadyPrefixed ? pathname : (pathname === '/' ? '/docs' : `/docs${pathname}`)

    // Prefixos válidos dentro de /docs — qualquer outra rota redireciona pro domínio principal
    const docsBasePaths = [
      '/docs/introducao',
      '/docs/usuario',
      '/docs/pagamentos',
      '/docs/saques',
      '/docs/transferencias',
      '/docs/afiliados',
      '/docs/publico',
    ]
    const isDocsRoute = newPathname === '/docs' || docsBasePaths.some(base => newPathname.startsWith(base))

    if (!isDocsRoute) {
      return NextResponse.redirect(`https://amethys.lat${pathname}`)
    }

    const url = request.nextUrl.clone()
    url.pathname = newPathname

    return NextResponse.rewrite(url)
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    // Apenas interceptar rotas que não são arquivos estáticos ou rotas do Next.js
    '/((?!api|_next|favicon.ico|favicon.svg|robots.txt|sitemap.xml|manifest.json|icon.svg).*)',
  ],
}
