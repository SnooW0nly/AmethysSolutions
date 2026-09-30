'use client'

import { useEffect } from 'react'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // Log do erro para debugging
    console.error('Erro global capturado:', error)
  }, [error])

  return (
    <html lang="pt-BR">
      <body>
        <div className="flex items-center justify-center min-h-screen bg-background text-foreground p-6">
          <div className="text-center space-y-4 max-w-md">
            <h1 className="text-2xl font-bold">Erro crítico</h1>
            <p className="text-muted-foreground">
              Ocorreu um erro crítico na aplicação. Por favor, recarregue a página.
            </p>
            <div className="flex gap-2 justify-center">
              <button
                onClick={() => reset()}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
              >
                Tentar novamente
              </button>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-foreground/5 text-foreground border border-foreground/10 rounded-lg hover:bg-foreground/10 transition-colors"
              >
                Recarregar página
              </button>
            </div>
          </div>
        </div>
      </body>
    </html>
  )
}

