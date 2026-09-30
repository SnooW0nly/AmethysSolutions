'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faBars, faXmark, faSearch, faBook, faShieldHalved,
  faGauge, faTriangleExclamation, faWebhook, faUser,
  faMoneyBillTransfer, faArrowDown, faArrowsLeftRight,
  faUserGroup, faChartBar, faChevronDown, faChevronRight,
  faArrowUpRightFromSquare, faKey, faCircle
} from '@fortawesome/free-solid-svg-icons'
import { Logo } from '@/components/icons'

interface NavItem {
  label: string
  href: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
}

interface NavSection {
  label: string
  icon: any
  items: NavItem[]
  basePath: string
}

const navSections: NavSection[] = [
  {
    label: 'Introdução',
    icon: faBook,
    basePath: '/docs/introducao',
    items: [
      { label: 'Visão Geral', href: '/docs/introducao/visao-geral' },
      { label: 'Autenticação', href: '/docs/introducao/autenticacao' },
      { label: 'Rate Limits', href: '/docs/introducao/rate-limits' },
      { label: 'Tratamento de Erros', href: '/docs/introducao/erros' },
      { label: 'Webhooks', href: '/docs/introducao/webhooks' },
    ]
  },
  {
    label: 'Usuário',
    icon: faUser,
    basePath: '/docs/usuario',
    items: [
      { label: 'Registrar', href: '/docs/usuario/registrar', method: 'POST' },
      { label: 'Obter dados', href: '/docs/usuario/obter', method: 'GET' },
      { label: 'Atualizar', href: '/docs/usuario/atualizar', method: 'PUT' },
      { label: 'Saldo', href: '/docs/usuario/saldo', method: 'GET' },
      { label: 'Transações', href: '/docs/usuario/transacoes', method: 'GET' },
    ]
  },
  {
    label: 'Pagamentos PIX',
    icon: faMoneyBillTransfer,
    basePath: '/docs/pagamentos',
    items: [
      { label: 'Criar cobrança', href: '/docs/pagamentos/criar', method: 'POST' },
      { label: 'Consultar', href: '/docs/pagamentos/consultar', method: 'GET' },
      { label: 'Listar', href: '/docs/pagamentos/listar', method: 'GET' },
      { label: 'Enviar PIX', href: '/docs/pagamentos/enviar', method: 'POST' },
    ]
  },
  {
    label: 'Saques',
    icon: faArrowDown,
    basePath: '/docs/saques',
    items: [
      { label: 'Sacar via PIX', href: '/docs/saques/pix', method: 'POST' },
      { label: 'Sacar em Crypto', href: '/docs/saques/crypto', method: 'POST' },
      { label: 'Consultar', href: '/docs/saques/consultar', method: 'GET' },
      { label: 'Listar', href: '/docs/saques/listar', method: 'GET' },
    ]
  },
  {
    label: 'Transferências',
    icon: faArrowsLeftRight,
    basePath: '/docs/transferencias',
    items: [
      { label: 'Transferência Interna', href: '/docs/transferencias/interna', method: 'POST' },
    ]
  },
  {
    label: 'Afiliados',
    icon: faUserGroup,
    basePath: '/docs/afiliados',
    items: [
      { label: 'Registrar', href: '/docs/afiliados/registrar', method: 'POST' },
      { label: 'Meus dados', href: '/docs/afiliados/meus-dados', method: 'GET' },
      { label: 'Estatísticas', href: '/docs/afiliados/estatisticas', method: 'GET' },
      { label: 'Atualizar código', href: '/docs/afiliados/atualizar-codigo', method: 'PUT' },
      { label: 'Validar código', href: '/docs/afiliados/validar-codigo', method: 'GET' },
    ]
  },
  {
    label: 'Público',
    icon: faChartBar,
    basePath: '/docs/publico',
    items: [
      { label: 'Estatísticas', href: '/docs/publico/estatisticas', method: 'GET' },
    ]
  },
]

const methodColors: Record<string, string> = {
  GET: 'bg-emerald-500/15 text-emerald-400',
  POST: 'bg-blue-500/15 text-blue-400',
  PUT: 'bg-amber-500/15 text-amber-400',
  DELETE: 'bg-red-500/15 text-red-400',
}

function SidebarContent({ onClose }: { onClose?: () => void }) {
  const pathname = usePathname()
  const [search, setSearch] = useState('')
  const [openSections, setOpenSections] = useState<Set<string>>(new Set(navSections.map(s => s.label)))

  const toggleSection = (label: string) => {
    setOpenSections(prev => {
      const next = new Set(prev)
      next.has(label) ? next.delete(label) : next.add(label)
      return next
    })
  }

  const filtered = navSections.map(section => ({
    ...section,
    items: section.items.filter(item =>
      !search || item.label.toLowerCase().includes(search.toLowerCase())
    )
  })).filter(section => !search || section.items.length > 0)

  return (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="h-14 flex items-center px-5 border-b border-foreground/10 gap-3 flex-shrink-0">
        <Link href="/" className="flex items-center gap-3 select-none">
          <Logo size={32} width={32} height={32} />
          <div className="flex flex-col leading-[14px]">
            <span className="text-foreground/90 font-normal text-[13px]">Amethys</span>
            <span className="text-foreground/50 font-normal text-[11px]">API Reference</span>
          </div>
        </Link>
        {onClose && (
          <button onClick={onClose} className="ml-auto p-1.5 rounded-md hover:bg-foreground/5 text-foreground/50 lg:hidden">
            <FontAwesomeIcon icon={faXmark} className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Search */}
      <div className="px-4 py-3 border-b border-foreground/10 flex-shrink-0">
        <div className="relative">
          <FontAwesomeIcon icon={faSearch} className="absolute left-3 top-1/2 -translate-y-1/2 w-3 h-3 text-foreground/30" />
          <input
            type="text"
            placeholder="Buscar endpoint..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full bg-foreground/5 border border-foreground/10 rounded-lg pl-8 pr-3 py-2 text-[12px] text-foreground placeholder-foreground/30 outline-none focus:border-primary/40 transition-colors"
          />
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-track]:transparent [&::-webkit-scrollbar-thumb]:bg-foreground/10">
        {filtered.map(section => {
          const isOpen = openSections.has(section.label) || !!search
          const hasActive = section.items.some(i => pathname === i.href)

          return (
            <div key={section.label} className="mb-1">
              <button
                onClick={() => toggleSection(section.label)}
                className="w-full flex items-center gap-2 px-4 py-2 text-[11px] font-semibold text-foreground/40 uppercase tracking-widest hover:text-foreground/60 transition-colors group"
              >
                <FontAwesomeIcon icon={section.icon} className="w-3 h-3" />
                <span>{section.label}</span>
                <FontAwesomeIcon
                  icon={faChevronDown}
                  className={`w-2.5 h-2.5 ml-auto transition-transform duration-200 ${isOpen ? '' : '-rotate-90'}`}
                />
              </button>

              {isOpen && (
                <div className="pb-1">
                  {section.items.map(item => {
                    const isActive = pathname === item.href
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        onClick={onClose}
                        className={`flex items-center gap-2.5 pl-8 pr-4 py-1.5 text-[12.5px] transition-all border-l-2 mx-0 ${
                          isActive
                            ? 'text-primary border-primary bg-primary/5'
                            : 'text-foreground/60 border-transparent hover:text-foreground hover:bg-foreground/5 hover:border-foreground/10'
                        }`}
                      >
                        <span className="flex-1">{item.label}</span>
                        {item.method && (
                          <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded ${methodColors[item.method]}`}>
                            {item.method}
                          </span>
                        )}
                      </Link>
                    )
                  })}
                </div>
              )}
            </div>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-foreground/10 flex-shrink-0">
        <div className="flex items-center justify-between text-[11px] text-foreground/30">
          <span className="font-mono">v1.0</span>
          <Link
            href="https://amethys.lat"
            target="_blank"
            className="flex items-center gap-1 hover:text-foreground/60 transition-colors"
          >
            Portal
            <FontAwesomeIcon icon={faArrowUpRightFromSquare} className="w-2.5 h-2.5" />
          </Link>
        </div>
      </div>
    </div>
  )
}

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex min-h-screen bg-background">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed top-0 left-0 bottom-0 w-64 z-50
        bg-background border-r border-foreground/10
        flex flex-col
        transition-transform duration-300
        lg:translate-x-0 lg:sticky lg:top-0 lg:h-screen
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <SidebarContent onClose={() => setSidebarOpen(false)} />
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="sticky top-0 z-30 bg-background/80 backdrop-blur border-b border-foreground/10 h-14 flex items-center px-4 md:px-6 gap-4">
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-2 rounded-lg hover:bg-foreground/5 text-foreground/60"
          >
            <FontAwesomeIcon icon={faBars} className="w-4 h-4" />
          </button>

          {/* Breadcrumb area */}
          <div className="flex items-center gap-2 text-[12px] text-foreground/40 font-mono">
            <span className="text-foreground/30">api.amethys.lat</span>
            <span>/</span>
            <span>api</span>
            <span>/</span>
            <span>v1</span>
          </div>

          <div className="ml-auto flex items-center gap-3">
            <span className="hidden sm:flex items-center gap-1.5 text-[11px] font-mono bg-foreground/5 border border-foreground/10 px-2.5 py-1 rounded-md text-foreground/50">
              <FontAwesomeIcon icon={faCircle} className="w-1.5 h-1.5 text-emerald-400" />
              v1.0
            </span>
            <Link
              href="https://amethys.lat"
              target="_blank"
              className="hidden sm:flex items-center gap-1.5 text-[12px] bg-primary text-primary-foreground px-3 py-1.5 rounded-lg hover:bg-primary/90 transition-colors font-medium"
            >
              Portal
              <FontAwesomeIcon icon={faArrowUpRightFromSquare} className="w-2.5 h-2.5" />
            </Link>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1">
          {children}
        </main>
      </div>
    </div>
  )
}
