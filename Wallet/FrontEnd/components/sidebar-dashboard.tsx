'use client'

import { useState, useEffect } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faHome, faReceipt, faArrowUp, faSignOutAlt, faStore, faUser, faComment, faSliders, faBullhorn, faBagShopping, faRobot, faWrench, faBrush, faDollar, faFolder, faTag, faBox, faPlug, faUsers, faKey, faExternalLink, faXmark, faBullseye, faChartLine, faArrowDown, faExchangeAlt, faGear, faLayerGroup, faChevronDown } from '@fortawesome/free-solid-svg-icons'
import { faDiscord } from '@fortawesome/free-brands-svg-icons'
import { RippleButton } from './ripple-button'
import { Separator } from '@/components/ui/separator'
import { Logo } from './icons'
import { useAuth } from '@/hooks/useAuth'

interface SidebarDashboardProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function SidebarDashboard({ open, onOpenChange }: SidebarDashboardProps) {
  const router = useRouter()
  const pathname = usePathname()
  const { logout } = useAuth()

  const categories = [
    {
      title: 'Plataforma',
      icon: faLayerGroup,
      items: [
        { id: 'inicio', label: 'Início', icon: faHome, href: '/dashboard' },
        { id: 'resumo', label: 'Resumo', icon: faChartLine, href: '/dashboard/summary' },
        { id: 'extrato', label: 'Extrato', icon: faReceipt, href: '/dashboard/transactions' },
        { id: 'metas', label: 'Metas', icon: faBullseye, href: '/dashboard/goals' },
        { id: 'afiliados', label: 'Programa de Afiliados', icon: faDollar, href: '/dashboard/affiliates-program' },
      ]
    },
    {
      title: 'Transações',
      icon: faExchangeAlt,
      items: [
        { id: 'transferir', label: 'Transferir', icon: faArrowUp, href: '/dashboard/transfer' },
        { id: 'depositar', label: 'Depositar', icon: faArrowDown, href: '/dashboard/deposit' },
      ]
    },
    {
      title: 'Integrações',
      icon: faPlug,
      items: [
        { id: 'credenciais', label: 'Credenciais', icon: faKey, href: '/dashboard/credentials' },
      //  { id: 'docs', label: 'Ver Documentação', icon: faExternalLink, href: 'https://docs.amethys.lat', external: true },
       // { id: 'discord', label: 'Discord Bot', icon: faRobot, href: 'https://discord.com/oauth2/authorize?client_id=1448484905414561832&permissions=8&scope=bot%20applications.commands', external: true },
      ]
    },

  ]

  // Categories that should be collapsed by default
  const defaultCollapsed = ['Checkout']
  const STORAGE_KEY = 'sidebar_collapsed_categories'

  // Find which category contains the current page
  const findCategoryForPath = (path: string) => {
    for (const category of categories) {
      if (category.items.some(item => !item.external && item.href === path)) {
        return category.title
      }
    }
    return null
  }

  // Initialize collapsed state from sessionStorage or defaults
  const [collapsedCategories, setCollapsedCategories] = useState<Set<string>>(() => {
    // Try to load from sessionStorage first
    if (typeof window !== 'undefined') {
      const saved = sessionStorage.getItem(STORAGE_KEY)
      if (saved) {
        try {
          const parsed = JSON.parse(saved) as string[]
          const savedSet = new Set(parsed)
          // Still expand if current page is in a collapsed category
          const currentCategory = findCategoryForPath(pathname)
          if (currentCategory && savedSet.has(currentCategory)) {
            savedSet.delete(currentCategory)
          }
          return savedSet
        } catch (e) {
          // Ignore parse errors
        }
      }
    }

    // Default: expand if current page is in that category
    const currentCategory = findCategoryForPath(pathname)
    const initialCollapsed = new Set(defaultCollapsed)
    if (currentCategory && initialCollapsed.has(currentCategory)) {
      initialCollapsed.delete(currentCategory)
    }
    return initialCollapsed
  })

  // Save to sessionStorage whenever collapsed state changes
  useEffect(() => {
    if (typeof window !== 'undefined') {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify([...collapsedCategories]))
    }
  }, [collapsedCategories])

  // Effect to expand category when navigating to a page within it
  useEffect(() => {
    const currentCategory = findCategoryForPath(pathname)
    if (currentCategory && collapsedCategories.has(currentCategory)) {
      setCollapsedCategories(prev => {
        const newSet = new Set(prev)
        newSet.delete(currentCategory)
        return newSet
      })
    }
  }, [pathname])

  const toggleCategory = (title: string) => {
    setCollapsedCategories(prev => {
      const newSet = new Set(prev)
      if (newSet.has(title)) {
        newSet.delete(title)
      } else {
        newSet.add(title)
      }
      return newSet
    })
  }
  const handleLogout = async () => {
    await logout()
  }

  return (
    <>
      {/* Mobile Overlay */}
      {open && (
        <div
          className="fixed inset-0 bg-black/40 lg:hidden z-40"
          onClick={() => onOpenChange(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 w-full lg:w-64 bg-background transition-all duration-300 z-50 flex flex-col ${open ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
          }`}
      >
        {/* Logo & Close Button */}
        <div className="h-14 flex items-center justify-between px-4 lg:px-6 border-b border-foreground/10">
          <div className="flex justify-start items-center gap-3 cursor-pointer select-none" onClick={() => router.push('/')}>
            <Logo size={38} width={38} height={38} />
            <div className="flex flex-col leading-[15px]">
              <span className="text-foreground/90 font-normal font-sans text-[13px]">
                Amethys
              </span>
              <span className="text-foreground/60 font-normal font-sans text-[12px]">
                Wallet
              </span>
            </div>
          </div>

          {/* Close Button - Only visible on mobile */}
          <button
            onClick={() => onOpenChange(false)}
            className="lg:hidden p-2 rounded-md hover:bg-foreground/5 transition-colors"
            aria-label="Fechar menu"
          >
            <FontAwesomeIcon icon={faXmark} className="w-4 h-4 text-foreground" />
          </button>
        </div>

        {/* Menu Items */}
        <nav
          className="flex-1 overflow-y-auto px-4 pt-4 pb-6 relative border-r border-foreground/10 space-y-6 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]"
        >
          {categories.map((category) => {
            const isCollapsed = collapsedCategories.has(category.title)
            const isCollapsible = !['Plataforma'].includes(category.title)

            return (
              <div key={category.title} className="space-y-1">
                {isCollapsible ? (
                  <button
                    onClick={() => toggleCategory(category.title)}
                    className="w-full px-4 mb-2 flex items-center justify-between text-xs font-semibold text-foreground/50 uppercase tracking-wider hover:text-foreground/70 transition-colors cursor-pointer"
                  >
                    <div className="flex items-center gap-2">
                      <FontAwesomeIcon icon={category.icon} className="w-3 h-3" />
                      <span>{category.title}</span>
                    </div>
                    <FontAwesomeIcon
                      icon={faChevronDown}
                      className="w-3 h-3 transition-transform duration-200"
                      style={{ transform: isCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)' }}
                    />
                  </button>
                ) : (
                  <div className="px-4 mb-2 flex items-center gap-2 text-xs font-semibold text-foreground/50 uppercase tracking-wider">
                    <FontAwesomeIcon icon={category.icon} className="w-3 h-3" />
                    <span>{category.title}</span>
                  </div>
                )}

                {(!isCollapsible || !isCollapsed) && category.items.map((item) => {
                  const isActive = pathname === item.href

                  if (item.external) {
                    return (
                      <a
                        key={item.id}
                        href={item.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={() => onOpenChange(false)}
                        className="w-full flex items-center gap-3 px-4 py-2 text-sm hover:bg-foreground/5 transition-colors group text-foreground/70 hover:text-foreground rounded-lg"
                      >
                        <FontAwesomeIcon icon={item.icon} className="w-4 h-4" />
                        <span>{item.label}</span>
                      </a>
                    )
                  }

                  return (
                    <RippleButton
                      key={item.id}
                      onClick={() => router.push(item.href)}
                      className={`w-full flex items-center gap-3 px-4 py-2 text-sm transition-all relative group rounded-lg ${isActive
                        ? 'text-primary bg-foreground/5'
                        : 'text-foreground/70 hover:text-foreground hover:bg-foreground/5'
                        }`}
                    >
                      <FontAwesomeIcon icon={item.icon} className="w-4 h-4" />
                      <span>{item.label}</span>
                    </RippleButton>
                  )
                })}
              </div>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="p-4 border-r border-foreground/10 space-y-2">
          <Separator className="bg-foreground/10 mb-2" />

          <RippleButton
            onClick={() => {
              onOpenChange(false)
              router.push('/dashboard/settings')
            }}
            className={`w-full flex items-center gap-3 px-4 py-2 text-sm transition-all relative group rounded-lg ${pathname === '/dashboard/settings'
              ? 'text-primary bg-foreground/5'
              : 'text-foreground/70 hover:text-foreground hover:bg-foreground/5'
              }`}
          >
            <FontAwesomeIcon icon={faGear} className="w-4 h-4" />
            <span className="text-sm font-medium">Configurações</span>
          </RippleButton>

          <a
            href="https://discord.gg/pxMbjuh4BK"
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => onOpenChange(false)}
            className="w-full flex items-center gap-3 px-4 py-2 rounded-lg text-foreground/70 hover:text-[#5865F2] hover:bg-[#5865F2]/10 transition-colors"
          >
            <FontAwesomeIcon icon={faDiscord} className="w-4 h-4" />
            <span className="text-sm font-medium">Suporte no Discord</span>
          </a>

          <RippleButton
            onClick={() => {
              onOpenChange(false)
              handleLogout()
            }}
            className="w-full flex items-center gap-3 px-4 py-2 rounded-lg text-red-500 hover:bg-red-500/10 transition-colors"
          >
            <FontAwesomeIcon icon={faSignOutAlt} className="w-4 h-4" />
            <span className="text-sm font-medium">Encerrar Sessão</span>
          </RippleButton>
        </div>
      </aside>
    </>
  )
}
