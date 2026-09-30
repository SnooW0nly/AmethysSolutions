/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  turbopack: {
    root: process.cwd(),
  },
  // Melhorar tratamento de erros durante build
  reactStrictMode: true,
  // Suprimir avisos de hidratação em desenvolvimento após build
  onDemandEntries: {
    maxInactiveAge: 25 * 1000,
    pagesBufferLength: 2,
  },
  // Configurações para melhorar estabilidade após build
  experimental: {
    // Evitar problemas de hidratação
    optimizePackageImports: ['@fortawesome/react-fontawesome'],
  },
  // Headers de cache para evitar problemas de cache em deployments
  async headers() {
    return [
      {
        // Service Worker - não cachear
        source: '/sw.js',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-cache, no-store, must-revalidate',
          },
        ],
      },
      {
        // Todas as páginas - não cachear HTML
        source: '/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'no-cache, no-store, must-revalidate',
          },
          {
            key: 'Pragma',
            value: 'no-cache',
          },
          {
            key: 'Expires',
            value: '0',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
        ],
      },
    ]
  },
}

export default nextConfig
