'use client'

import { usePathname } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { Skeleton } from '@/components/ui/skeleton'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faSun, faMoon } from '@fortawesome/free-solid-svg-icons'
import { useState, useEffect } from 'react'

interface Tab {
  label: string
  href: string
  description: string
  active?: boolean
}

interface DashboardHeaderProps {
  loading?: boolean
}

export function DashboardHeader({ loading = false }: DashboardHeaderProps) {
  const pathname = usePathname()
  const { user } = useAuth()
  const [isDaytime, setIsDaytime] = useState(true)

  useEffect(() => {
    const updateTimeOfDay = () => {
      const hour = new Date().getHours()
      setIsDaytime(hour >= 6 && hour < 18)
    }

    updateTimeOfDay()
    // Atualizar a cada minuto para manter sincronizado
    const interval = setInterval(updateTimeOfDay, 60000)
    return () => clearInterval(interval)
  }, [])

  const tabs: Tab[] = [
    {
      label: 'Início',
      href: '/dashboard',
      description: 'Visão geral da sua conta e transações',
    },
    {
      label: 'Resumo',
      href: '/dashboard/summary',
      description: 'Análise detalhada das suas finanças',
    },
    {
      label: 'Extrato',
      href: '/dashboard/transactions',
      description: 'Visualize todas as suas transações',
    },
    {
      label: 'Metas',
      href: '/dashboard/goals',
      description: 'Acompanhe suas metas de faturamento e conquiste suas recompensas',
    },
    {
      label: 'Transferir',
      href: '/dashboard/transfer',
      description: 'Envie dinheiro para outras contas',
    },
    {
      label: 'Depositar',
      href: '/dashboard/deposit',
      description: 'Adicione dinheiro à sua conta',
    },
    {
      label: 'Suas Credenciais',
      href: '/dashboard/credentials',
      description: 'Utilize estas credenciais para autenticar suas requisições à API.',
    },
  ]

  const activeTab = tabs.find((tab) => pathname === tab.href || (tab.href === '/dashboard' && pathname === '/dashboard'))

  // Handle settings page
  const isSettings = pathname === '/dashboard/settings'
  const isDashboard = pathname === '/dashboard'

  // Obter primeiro nome do usuário
  const getFirstName = (fullName: string | undefined) => {
    if (!fullName) return ''
    return fullName.split(' ')[0]
  }

  const firstName = getFirstName(user?.fullName)
  let greeting = 'Bom dia'
  const currentHour = new Date().getHours()
  if (currentHour >= 12 && currentHour < 18) {
    greeting = 'Boa tarde'
  } else if (currentHour >= 18 || currentHour < 6) {
    greeting = 'Boa noite'
  }
  const timeIcon = isDaytime ? faSun : faMoon

  const displayTitle = isSettings
    ? 'Configurações'
    : isDashboard && firstName
      ? `${greeting}, ${firstName}!`
      : (activeTab?.label || 'Dashboard')
  const displayDescription = isSettings
    ? 'Gerencie suas preferências e configurações'
    : (activeTab?.description || 'Gerencie sua conta Amethys Wallet')

  return (
    <header className="items-center border-b border-foreground/10 mb-4 pb-4">
      <div className="mb-2 md:mb-0">
        {loading ? (
          <>
            <Skeleton className="h-8 w-48 mb-2" />
            <Skeleton className="h-4 w-96" />
          </>
        ) : (
          <>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{displayTitle}</h1>
              {isDashboard && firstName && (
                <FontAwesomeIcon
                  icon={timeIcon}
                  className={`w-8 h-8 ${isDaytime ? 'text-yellow-500' : 'text-blue-400'}`}
                />
              )}
            </div>
            <p className="text-foreground/70 text-sm mt-1">{displayDescription}</p>
          </>
        )}
      </div>
    </header>
  )
}
