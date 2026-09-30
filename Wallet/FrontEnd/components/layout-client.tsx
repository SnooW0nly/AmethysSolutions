'use client'

import { usePathname } from 'next/navigation'
import { Navbar } from './navbar'
import { Footer } from './footer'
import { PWAProvider } from './pwa-provider'
import { Toaster } from '@/components/ui/toaster'
import { ErrorBoundary } from '@/components/error-boundary'

export default function LayoutClient({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  const hideLayout = pathname?.startsWith('/dashboard')
  const isHome = pathname === '/'
  const isLogin = pathname === '/login'
  const isSignup = pathname === '/signup'

  return (
    <ErrorBoundary>
      <PWAProvider>
        <div className={`relative flex flex-col ${hideLayout ? 'h-screen overflow-hidden' : 'min-h-screen'}`}>
          {!hideLayout && <Navbar />}
          <div className="overflow-x-hidden flex-grow flex flex-col">
            {hideLayout ? (
              children
            ) : (
              <main className={`flex-grow ${isHome ? 'mt-[-30] md:mt-0' : (isLogin || isSignup) ? 'mt-4 md:mt-6' : 'mt-8 md:mt-12'} mb-10 ${isHome ? '' : 'container mx-auto max-w-7xl px-4 sm:px-6'}`}>
                <div className={isHome ? 'max-w-7xl mx-auto px-6' : ''}>
                  {children}
                </div>
              </main>
            )}
            {!hideLayout && <Footer />}
          </div>
        </div>
        <Toaster />
      </PWAProvider>
    </ErrorBoundary>
  )
}

