'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { 
  faChevronUp, 
  faGear, 
  faRightFromBracket,
  faUser,
  faChartLine,
  faHome,
  faCreditCard,
} from '@fortawesome/free-solid-svg-icons'
import { useAuth } from '@/hooks/useAuth'
import { Skeleton } from '@/components/ui/skeleton'
import { RippleButton } from '@/components/ripple-button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { ErrorBoundary } from '@/components/error-boundary'

function UserMenuContent() {
  const { user, loading, logout } = useAuth()
  const [isOpen, setIsOpen] = useState(false)
  const router = useRouter()

  // Se estiver carregando, mostrar skeleton
  if (loading) {
    return (
      <Skeleton className="rounded-md">
        <div className="w-8 h-8 rounded-md bg-foreground/10" />
      </Skeleton>
    )
  }

  // Se não houver usuário (não autenticado ou erro), mostrar botão de login
  // Isso inclui casos onde o backend está indisponível
  if (!user) {
    return (
      <Link href="/login">
        <RippleButton className="px-5 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors text-sm inline-flex items-center gap-2">
          <FontAwesomeIcon icon={faUser} className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Iniciar sessão</span>
          <span className="sm:hidden">Entrar</span>
        </RippleButton>
      </Link>
    )
  }

  // Obter iniciais do nome
  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)
  }

  // Construir URL do avatar
  const getAvatarUrl = () => {
    if (!user.avatar) return undefined
    
    // Se o avatar já é uma URL completa (http/https), retornar como está
    if (user.avatar.startsWith('http://') || user.avatar.startsWith('https://')) {
      return user.avatar
    }
    
    // Se começa com /, adicionar backend URL
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:3001'
    return `${backendUrl}${user.avatar.startsWith('/') ? user.avatar : `/${user.avatar}`}`
  }

  const handleLogout = async () => {
    await logout()
    setIsOpen(false)
  }

  return (
    <DropdownMenu open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuTrigger asChild>
        <button className="flex items-center gap-1 cursor-pointer hover:opacity-80 transition-opacity">
          <Avatar className="h-8 w-8 rounded-md" key={`avatar-${user.avatar || 'no-avatar'}-${user.updatedAt || Date.now()}`}>
            <AvatarImage 
              src={getAvatarUrl()} 
              alt={user.fullName}
              key={`avatar-img-${user.avatar || 'no-avatar'}-${user.updatedAt || Date.now()}`}
            />
            <AvatarFallback className="bg-primary/20 text-primary rounded-md text-xs">
              {getInitials(user.fullName)}
            </AvatarFallback>
          </Avatar>
          <FontAwesomeIcon
            icon={faChevronUp}
            className={`text-xs transition-transform duration-200 text-foreground/60 ${
              isOpen ? 'rotate-0' : 'rotate-180'
            }`}
          />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        className="w-56 bg-background border border-foreground/10"
      >
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium leading-none text-foreground truncate max-w-[200px]">
              {user.fullName}
            </p>
            <p className="text-xs leading-none text-foreground/60 truncate max-w-[200px]">
              {user.email}
            </p>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        {/* Início item */}
        <DropdownMenuItem
          onClick={() => {
            router.push('/')
            setIsOpen(false)
          }}
          className="cursor-pointer focus:bg-foreground/5 hover:bg-foreground/5"
        >
          <FontAwesomeIcon icon={faHome} className="w-4 h-4 mr-2 text-primary" />
          <span>Início</span>
        </DropdownMenuItem>

        <DropdownMenuItem
          onClick={() => {
            router.push('/dashboard')
            setIsOpen(false)
          }}
          className="cursor-pointer focus:bg-foreground/5 hover:bg-foreground/5"
        >
          <FontAwesomeIcon icon={faChartLine} className="w-4 h-4 mr-2 text-primary" />
          <span>Dashboard</span>
        </DropdownMenuItem>

        <DropdownMenuItem
          onClick={() => {
            router.push('/pricing')
            setIsOpen(false)
          }}
          className="cursor-pointer focus:bg-foreground/5 hover:bg-foreground/5"
        >
          <FontAwesomeIcon icon={faCreditCard} className="w-4 h-4 mr-2 text-primary" />
          <span>Planos</span>
        </DropdownMenuItem>
        
        <DropdownMenuItem
          onClick={() => {
            router.push('/dashboard/settings')
            setIsOpen(false)
          }}
          className="cursor-pointer focus:bg-foreground/5 hover:bg-foreground/5"
        >
          <FontAwesomeIcon icon={faGear} className="w-4 h-4 mr-2 text-primary" />
          <span>Configurações</span>
        </DropdownMenuItem>

        <DropdownMenuSeparator />
        
        <DropdownMenuItem
          onClick={handleLogout}
          className="cursor-pointer text-red-500 focus:text-red-500 focus:bg-red-500/5 hover:bg-red-500/5"
        >
          <FontAwesomeIcon icon={faRightFromBracket} className="w-4 h-4 mr-2 text-red-500" />
          <span>Encerrar Sessão</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export function UserMenu() {
  return (
    <ErrorBoundary
      fallback={
        <Link href="/login">
          <RippleButton className="px-5 py-2 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 transition-colors text-sm inline-flex items-center gap-2">
            <FontAwesomeIcon icon={faUser} className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Iniciar sessão</span>
            <span className="sm:hidden">Entrar</span>
          </RippleButton>
        </Link>
      }
    >
      <UserMenuContent />
    </ErrorBoundary>
  )
}

