'use client'

import { Component, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Não logar erros durante SSR/build
    if (typeof window === 'undefined') {
      return
    }

    console.error('ErrorBoundary capturou um erro:', error, errorInfo)
    
    // Se for erro de chunk, não recarregar automaticamente em desenvolvimento
    const isChunkError = 
      error.message?.includes('Failed to load chunk') || 
      error.message?.includes('Loading chunk') ||
      error.message?.includes('ChunkLoadError') ||
      error.message?.includes('_next/static/chunks') ||
      error.message?.includes('react-server-dom-turbopack')
    
    if (isChunkError) {
      if (process.env.NODE_ENV === 'production') {
        console.log('Erro de chunk detectado, recarregando página...')
        setTimeout(() => {
          if (typeof window !== 'undefined') {
            window.location.reload()
          }
        }, 1000)
      } else {
        console.warn('Erro de chunk do Turbopack em desenvolvimento (ignorado):', error.message)
      }
      return
    }

    // Se for erro de hidratação, tentar recarregar apenas uma vez
    if (error.message?.includes('Hydration') || 
        error.message?.includes('hydration') ||
        error.message?.includes('Hydration failed') ||
        errorInfo.componentStack?.includes('hydration')) {
      console.log('Erro de hidratação detectado, recarregando página...')
      // Evitar loop infinito de recarregamentos
      try {
        if (typeof window !== 'undefined' && window.sessionStorage) {
          const hasReloaded = sessionStorage.getItem('hydration_reload_attempted')
          if (!hasReloaded) {
            sessionStorage.setItem('hydration_reload_attempted', 'true')
            setTimeout(() => {
              if (typeof window !== 'undefined') {
                window.location.reload()
              }
            }, 1000)
          } else {
            console.warn('Erro de hidratação já tentou recarregar, não tentando novamente')
            sessionStorage.removeItem('hydration_reload_attempted')
          }
        }
      } catch (e) {
        // Se sessionStorage não estiver disponível, apenas logar
        console.warn('Não foi possível acessar sessionStorage:', e)
      }
      return
    }

    // Se for erro de servidor indisponível, não recarregar automaticamente
    if (error.message?.includes('Servidor indisponível') ||
        error.message?.includes('fetch') || 
        error.message?.includes('network') ||
        error.message?.includes('Failed to fetch') ||
        error.message?.includes('ECONNREFUSED') ||
        error.message?.includes('ERR_CONNECTION_REFUSED')) {
      console.warn('Erro de rede/servidor detectado, não recarregando automaticamente')
      return
    }

    // Se for erro de build/compilação, não recarregar
    if (error.message?.includes('Minified React error') ||
        error.message?.includes('Cannot read property') ||
        error.message?.includes('is not defined')) {
      console.error('Erro de compilação/build detectado:', error.message)
      return
    }
  }

  render() {
    if (this.state.hasError) {
      // Durante SSR, não renderizar erro, apenas retornar children
      if (typeof window === 'undefined') {
        return this.props.children
      }

      // Em desenvolvimento, se tiver fallback, usar ele
      if (this.props.fallback) {
        return this.props.fallback
      }

      // Em desenvolvimento, ignorar erros de chunk do Turbopack e mostrar children
      const isChunkError = 
        this.state.error?.message?.includes('Failed to load chunk') ||
        this.state.error?.message?.includes('ChunkLoadError') ||
        this.state.error?.message?.includes('_next/static/chunks') ||
        this.state.error?.message?.includes('react-server-dom-turbopack')
      
      if (process.env.NODE_ENV === 'development' && isChunkError) {
        console.warn('Erro de chunk do Turbopack em desenvolvimento (ignorado):', this.state.error?.message)
        return this.props.children
      }

      return (
        <div className="flex items-center justify-center min-h-screen bg-background text-foreground p-6">
          <div className="text-center space-y-4 max-w-md">
            <h1 className="text-2xl font-bold">Ops! Algo deu errado</h1>
            <p className="text-muted-foreground">
              {this.state.error?.message?.includes('Failed to load chunk') 
                ? 'Erro ao carregar recursos. Recarregando...'
                : this.state.error?.message?.includes('Hydration')
                ? 'Erro de renderização detectado. Recarregando...'
                : 'Ocorreu um erro inesperado. Por favor, recarregue a página.'}
            </p>
            <button
              onClick={() => {
                if (typeof window !== 'undefined') {
                  window.location.reload()
                }
              }}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
            >
              Recarregar Página
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

