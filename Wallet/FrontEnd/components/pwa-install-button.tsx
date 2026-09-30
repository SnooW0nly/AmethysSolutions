'use client'

import { useState, useEffect } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faDownload, faMobile, faDesktop } from '@fortawesome/free-solid-svg-icons'
import { usePWA } from '@/hooks/usePWA'

interface PWAInstallButtonProps {
  className?: string
  showIcon?: boolean
}

export function PWAInstallButton({ className = '', showIcon = true }: PWAInstallButtonProps) {
  const { isInstallable, isInstalled, install: installPWA } = usePWA()
  const [showInstructions, setShowInstructions] = useState(false)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  const handleClick = async () => {
    if (isInstallable) {
      await installPWA()
    } else {
      setShowInstructions(true)
    }
  }

  // Não renderizar até montar no cliente para evitar erro de hidratação
  if (!mounted) {
    return null
  }

  const getInstallInstructions = () => {
    if (typeof window === 'undefined') return { title: '', steps: [] }
    
    const userAgent = navigator.userAgent.toLowerCase()
    
    if (/iphone|ipad|ipod/.test(userAgent)) {
      return {
        title: 'Instalar no iOS',
        steps: [
          'Toque no botão de compartilhar',
          'Selecione "Adicionar à Tela de Início"',
          'Toque em "Adicionar"'
        ]
      }
    } else if (/android/.test(userAgent)) {
      return {
        title: 'Instalar no Android',
        steps: [
          'Toque no menu (3 pontos)',
          'Selecione "Instalar app" ou "Adicionar à tela inicial"',
          'Confirme a instalação'
        ]
      }
    } else {
      return {
        title: 'Instalar no navegador',
        steps: [
          'Procure pelo ícone de instalação na barra de endereços',
          'Ou use o menu do navegador',
          'Selecione "Instalar Amethys Wallet"'
        ]
      }
    }
  }

  // Não mostrar se já está instalado
  if (isInstalled) {
    return null
  }

  if (showInstructions) {
    const instructions = getInstallInstructions()
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowInstructions(false)}>
        <div className="bg-foreground border border-foreground/20 rounded-xl p-6 max-w-md w-full" onClick={(e) => e.stopPropagation()}>
          <h3 className="text-lg font-semibold text-foreground mb-4">{instructions.title}</h3>
          <ul className="space-y-3 mb-4">
            {instructions.steps.map((step, index) => (
              <li key={index} className="flex items-start gap-3 text-sm text-foreground/70">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/20 text-primary flex items-center justify-center text-xs font-semibold">
                  {index + 1}
                </span>
                <span>{step}</span>
              </li>
            ))}
          </ul>
          <button
            onClick={() => setShowInstructions(false)}
            className="w-full py-2 px-4 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            Fechar
          </button>
        </div>
      </div>
    )
  }

  return (
    <button
      onClick={handleClick}
      className={`text-foreground/70 hover:text-foreground hover:underline text-[14px] transition-colors flex items-center gap-1.5 ${className}`}
    >
      {showIcon && (
        <div className="flex items-center gap-1">
          <FontAwesomeIcon icon={faMobile} className="text-[14px]" />
          <FontAwesomeIcon icon={faDesktop} className="text-[14px]" />
        </div>
      )}
      <span>Baixar app</span>
    </button>
  )
}

