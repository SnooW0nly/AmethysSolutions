'use client'

import { useEffect } from 'react'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // Em desenvolvimento, ignorar erros de chunk do Turbopack
    if (process.env.NODE_ENV === 'development') {
      const errorMessage = error?.message || ''
      const isChunkError = 
        errorMessage.includes('Failed to load chunk') ||
        errorMessage.includes('ChunkLoadError') ||
        errorMessage.includes('_next/static/chunks') ||
        errorMessage.includes('react-server-dom-turbopack') ||
        errorMessage.includes('app_error_tsx')
      
      if (isChunkError) {
        console.warn('Erro de chunk do Turbopack em desenvolvimento (ignorado):', errorMessage)
        // Tentar resetar automaticamente após um pequeno delay
        setTimeout(() => {
          try {
            if (reset && typeof reset === 'function') {
              reset()
            } else if (typeof window !== 'undefined') {
              window.location.reload()
            }
          } catch (e) {
            // Se reset falhar, recarregar a página
            if (typeof window !== 'undefined') {
              window.location.reload()
            }
          }
        }, 500)
        return
      }
    }
    
    // Log do erro para debugging
    console.error('Erro capturado pelo error.tsx:', error)
  }, [error, reset])

  // Em desenvolvimento, se for erro de chunk, não mostrar a tela de erro
  if (process.env.NODE_ENV === 'development') {
    const errorMessage = error?.message || ''
    const isChunkError = 
      errorMessage.includes('Failed to load chunk') ||
      errorMessage.includes('ChunkLoadError') ||
      errorMessage.includes('_next/static/chunks') ||
      errorMessage.includes('react-server-dom-turbopack') ||
      errorMessage.includes('app_error_tsx')
    
    if (isChunkError) {
      // Retornar null e deixar o reset tentar recuperar
      return null
    }
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-background text-foreground p-6">
      <div className="text-center space-y-4 max-w-md">
        <h1 className="text-2xl font-bold">Ops! Algo deu errado</h1>
        <p className="text-muted-foreground">
          Ocorreu um erro ao carregar a página. Por favor, tente novamente.
        </p>
        {process.env.NODE_ENV === 'development' && error?.message && (
          <div className="p-4 bg-foreground/5 rounded-lg text-left">
            <p className="text-sm text-muted-foreground font-mono break-all">
              {error.message}
            </p>
          </div>
        )}
        <div className="flex gap-2 justify-center">
          <button
            onClick={() => {
              try {
                if (reset && typeof reset === 'function') {
                  reset()
                } else if (typeof window !== 'undefined') {
                  window.location.reload()
                }
              } catch (e) {
                if (typeof window !== 'undefined') {
                  window.location.reload()
                }
              }
            }}
            className="w-full px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
          >
            Tentar novamente
          </button>
          <button
            onClick={() => {
              if (typeof window !== 'undefined') {
                window.location.reload()
              }
            }}
            className="w-full px-4 py-2 bg-foreground/5 text-foreground border border-foreground/10 rounded-lg hover:bg-foreground/10 transition-colors"
          >
            Recarregar página
          </button>
        </div>
      </div>
    </div>
  )
}

