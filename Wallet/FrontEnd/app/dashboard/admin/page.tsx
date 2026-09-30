'use client'

import { Suspense, useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faUsers, faChartBar, faBars, faTimes, faFileAlt, faLayerGroup } from '@fortawesome/free-solid-svg-icons'
import { useRequireAdmin } from '@/hooks/useAdmin'
import { Loading } from '@/components/loading'
import dynamic from 'next/dynamic'

const UsuariosSection = dynamic(() => import('./sections/UsuariosSection').then(m => ({ default: m.UsuariosSection })), { ssr: false })
const StatsSection = dynamic(() => import('./sections/StatsSection').then(m => ({ default: m.StatsSection })), { ssr: false })
const AuditSection = dynamic(() => import('./sections/AuditSection').then(m => ({ default: m.AuditSection })), { ssr: false })
const PlanosSection = dynamic(() => import('./sections/PlanosSection').then(m => ({ default: m.PlanosSection })), { ssr: false })

type AdminSection = 'usuarios' | 'stats' | 'audit' | 'planos'

function AdminPageContent() {
  const { user, loading, isAdmin } = useRequireAdmin()
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [selected, setSelected] = useState<AdminSection>('stats')
  const [contentReady, setContentReady] = useState(false)

  const sections: { id: AdminSection; label: string; icon: any }[] = [
    { id: 'stats', label: 'Estatísticas', icon: faChartBar },
    { id: 'usuarios', label: 'Usuários', icon: faUsers },
    { id: 'planos', label: 'Planos', icon: faLayerGroup },
    { id: 'audit', label: 'Auditoria', icon: faFileAlt },
  ]

  const title = sections.find((s) => s.id === selected)?.label

  useEffect(() => {
    if (!loading && isAdmin && user?.admin) {
      const timer = setTimeout(() => {
        setContentReady(true)
      }, 100)
      return () => clearTimeout(timer)
    } else {
      setContentReady(false)
    }
  }, [loading, isAdmin, user?.admin])

  if (loading || !isAdmin || !user?.admin || !contentReady) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="text-center space-y-4">
          <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-muted-foreground text-sm">Verificando permissões...</p>
        </div>
      </div>
    )
  }

  if (!user || !user.admin || !isAdmin) {
    return null
  }

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-50 w-64 bg-foreground/5 border-r border-foreground/10 transition-transform duration-300 ${
          isSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <div className="flex flex-col h-full p-3 md:p-4">
          <div className="flex items-center justify-between mb-4 md:mb-6">
            <h2 className="text-lg md:text-xl font-bold text-foreground">Painel Admin</h2>
            <button
              onClick={() => setIsSidebarOpen(false)}
              className="lg:hidden text-foreground/60 hover:text-foreground p-1"
            >
              <FontAwesomeIcon icon={faTimes} className="w-5 h-5" />
            </button>
          </div>

          <nav className="flex-1 space-y-1 md:space-y-2 overflow-y-auto">
            {sections.map((section) => (
              <button
                key={section.id}
                onClick={() => {
                  setSelected(section.id)
                  setIsSidebarOpen(false)
                }}
                className={`w-full flex items-center gap-2 md:gap-3 px-3 md:px-4 py-2 md:py-3 rounded-lg transition-colors text-sm md:text-base ${
                  selected === section.id
                    ? 'bg-primary text-primary-foreground'
                    : 'text-foreground/70 hover:bg-foreground/10 hover:text-foreground'
                }`}
              >
                <FontAwesomeIcon icon={section.icon} className="w-4 h-4 md:w-5 md:h-5 flex-shrink-0" />
                <span className="font-medium truncate">{section.label}</span>
              </button>
            ))}
          </nav>
        </div>
      </aside>

      {/* Overlay mobile */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Topbar */}
        <header className="h-14 md:h-16 border-b border-foreground/10 bg-foreground/2 flex items-center px-4 md:px-6">
          <button
            onClick={() => setIsSidebarOpen(true)}
            className="lg:hidden text-foreground/60 hover:text-foreground mr-3 md:mr-4 p-1"
          >
            <FontAwesomeIcon icon={faBars} className="w-5 h-5" />
          </button>
          <h1 className="text-lg md:text-xl font-bold text-foreground">{title}</h1>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto p-4 md:p-6">
          {selected === 'stats' && <StatsSection />}
          {selected === 'usuarios' && <UsuariosSection />}
          {selected === 'planos' && <PlanosSection />}
          {selected === 'audit' && <AuditSection />}
        </main>
      </div>
    </div>
  )
}

export default function AdminPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="text-center space-y-4">
          <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-muted-foreground text-sm">Verificando permissões...</p>
        </div>
      </div>
    }>
      <AdminPageContent />
    </Suspense>
  )
}
