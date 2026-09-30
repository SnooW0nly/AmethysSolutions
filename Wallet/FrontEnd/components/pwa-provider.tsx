'use client'

import { useEffect, useRef } from 'react'

export function PWAProvider({ children }: { children: React.ReactNode }) {
  const updateIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const messageHandlerRef = useRef<((event: MessageEvent) => void) | null>(null)

  useEffect(() => {
    if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
      // Registrar Service Worker com tratamento de erro melhorado
      navigator.serviceWorker
        .register('/sw.js')
        .then((registration) => {
          console.log('Service Worker registrado com sucesso:', registration.scope)
          
          // Verificar atualizações periodicamente
          updateIntervalRef.current = setInterval(() => {
            try {
              registration.update()
            } catch (error) {
              console.warn('Erro ao atualizar Service Worker:', error)
            }
          }, 60000) // A cada minuto
        })
        .catch((error) => {
          // Silenciar erros de Service Worker em desenvolvimento
          if (process.env.NODE_ENV === 'development') {
            console.warn('Service Worker não disponível em desenvolvimento:', error.message)
          } else {
            console.error('Erro ao registrar Service Worker:', error)
          }
        })

      // Escutar mensagens do Service Worker
      messageHandlerRef.current = (event: MessageEvent) => {
        try {
          console.log('Mensagem do Service Worker:', event.data)
        } catch (error) {
          console.warn('Erro ao processar mensagem do Service Worker:', error)
        }
      }
      
      try {
        navigator.serviceWorker.addEventListener('message', messageHandlerRef.current)
      } catch (error) {
        console.warn('Erro ao adicionar listener do Service Worker:', error)
      }

      // Cleanup quando o componente desmontar
      return () => {
        if (updateIntervalRef.current) {
          clearInterval(updateIntervalRef.current)
          updateIntervalRef.current = null
        }
        if (messageHandlerRef.current) {
          try {
            navigator.serviceWorker.removeEventListener('message', messageHandlerRef.current)
          } catch (error) {
            console.warn('Erro ao remover listener do Service Worker:', error)
          }
          messageHandlerRef.current = null
        }
      }
    }
  }, [])

  return <>{children}</>
}

