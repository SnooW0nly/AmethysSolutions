'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { isAuthenticated } from '@/lib/auth'
import { useAuth } from '@/hooks/useAuth'

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const { user, loading: authLoading } = useAuth()
  // Usar estado para rastrear se já foi hidratado no cliente
  const [isMounted, setIsMounted] = useState(false)
  const [isChecking, setIsChecking] = useState(false)
  const [isAuthenticatedState, setIsAuthenticatedState] = useState<boolean | null>(null)
  const [hasError, setHasError] = useState(false)

  // Marcar como montado após hidratação
  useEffect(() => {
    setIsMounted(true)
  }, [])

  useEffect(() => {
    // Só verificar autenticação após montagem no cliente
    if (!isMounted) return

    let mounted = true

    const checkAuth = async () => {
      try {
        // Marcar como verificando
        if (mounted) {
          setIsChecking(true)
        }

        // Aguardar useAuth terminar de carregar
        let waitCount = 0
        const maxWait = 15 // Máximo 15 tentativas (7.5 segundos)
        
        while (authLoading && waitCount < maxWait && mounted) {
          await new Promise(resolve => setTimeout(resolve, 500))
          waitCount++
        }

        // Pequeno delay adicional para garantir que tudo está sincronizado
        await new Promise(resolve => setTimeout(resolve, 200))

        if (!mounted) return

        // Verificar tanto token quanto usuário do useAuth
        const hasToken = isAuthenticated()
        const hasUser = !!user
        const authenticated = hasToken || hasUser
        
        if (mounted) {
          setIsAuthenticatedState(authenticated)
          setIsChecking(false)
          
          if (!authenticated) {
            // Redirecionar se não estiver autenticado
            router.replace('/login')
          }
        }
      } catch (error) {
        console.error('Erro no ProtectedRoute:', error)
        if (mounted) {
          // Em caso de erro, verificar novamente se tem token ou usuário
          const hasToken = isAuthenticated()
          const hasUser = !!user
          setIsAuthenticatedState(hasToken || hasUser)
          setIsChecking(false)
          
          if (!hasToken && !hasUser) {
            router.replace('/login')
          }
        }
      }
    }

    checkAuth()

    return () => {
      mounted = false
    }
  }, [router, isMounted, user, authLoading])

  // Se houver erro, mostrar mensagem ao invés de tela branca
  if (hasError) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background text-foreground p-6">
        <div className="text-center space-y-4 max-w-md">
          <h1 className="text-xl font-bold">Erro ao verificar autenticação</h1>
          <p className="text-muted-foreground text-sm">
            Por favor, recarregue a página.
          </p>
          <button
            onClick={() => {
              if (typeof window !== 'undefined') {
                window.location.reload()
              }
            }}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
          >
            Recarregar
          </button>
        </div>
      </div>
    )
  }

  // Durante SSR e antes da montagem no cliente, renderizar children diretamente
  // Isso garante que o HTML do servidor seja idêntico ao HTML inicial do cliente
  if (!isMounted) {
    return <>{children}</>
  }

  // Se useAuth ainda está carregando, aguardar
  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="text-center space-y-4">
          <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-muted-foreground text-sm">Carregando...</p>
        </div>
      </div>
    )
  }

  // Durante verificação inicial no cliente, mostrar loading
  // Mas apenas após a hidratação (isChecking === true e isAuthenticatedState === null)
  if (isChecking && isAuthenticatedState === null) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="text-center space-y-4">
          <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-muted-foreground text-sm">Verificando autenticação...</p>
        </div>
      </div>
    )
  }

  // Se não estiver autenticado após verificação, mostrar loading de redirecionamento
  if (isAuthenticatedState === false) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="text-center space-y-4">
          <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-muted-foreground text-sm">Redirecionando...</p>
        </div>
      </div>
    )
  }

  // Renderizar children normalmente (tanto no servidor quanto no cliente após verificação)
  return <>{children}</>
}

