'use client'

import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion'
import { useRef } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faHome, faReceipt, faArrowUp, faArrowDown, faSignOutAlt,
  faBullseye, faChartLine, faKey, faExchangeAlt, faLayerGroup,
  faChevronDown, faGear, faWallet, faEye, faArrowRight,
  faInbox, faBell, faChevronRight, faPlug, faDollar
} from '@fortawesome/free-solid-svg-icons'
import { faDiscord } from '@fortawesome/free-brands-svg-icons'

const SIMULATED_BALANCE = 4_738_52 // centavos → R$ 4.738,52
const SIMULATED_TRANSACTIONS = [
  { id: '1', type: 'received' as const, label: 'Depósito', amount: 25000, date: '14/05/2025 09:12', status: 'COMPLETED' },
  { id: '2', type: 'sent' as const, label: 'Transferência', amount: 8750, date: '13/05/2025 17:44', status: 'COMPLETED' },
  { id: '3', type: 'received' as const, label: 'Depósito', amount: 15000, date: '13/05/2025 11:30', status: 'COMPLETED' },
  { id: '4', type: 'sent' as const, label: 'Transferência', amount: 3200, date: '12/05/2025 20:05', status: 'COMPLETED' },
  { id: '5', type: 'received' as const, label: 'Comissão de Afiliado', amount: 4500, date: '12/05/2025 08:19', status: 'COMPLETED' },
]

function Logo({ size = 32 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 38 38" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect width="38" height="38" rx="10" fill="hsl(var(--primary))" fillOpacity="0.15" />
      <path d="M19 8L30 27H8L19 8Z" fill="hsl(var(--primary))" fillOpacity="0.9" />
      <path d="M19 16L25 27H13L19 16Z" fill="hsl(var(--primary))" />
    </svg>
  )
}

function Sidebar() {
  const navItems = [
    { label: 'Plataforma', icon: faLayerGroup, collapsible: false, items: [
      { label: 'Início', icon: faHome, active: true },
      { label: 'Resumo', icon: faChartLine },
      { label: 'Extrato', icon: faReceipt },
      { label: 'Metas', icon: faBullseye },
      { label: 'Programa de Afiliados', icon: faDollar },
    ]},
    { label: 'Transações', icon: faExchangeAlt, collapsible: true, items: [
      { label: 'Transferir', icon: faArrowUp },
      { label: 'Depositar', icon: faArrowDown },
    ]},
    { label: 'Integrações', icon: faPlug, collapsible: true, items: [
      { label: 'Credenciais', icon: faKey },
    ]},
  ]

  return (
    <div className="w-56 flex-shrink-0 flex flex-col bg-background border-r border-foreground/10 h-full">
      {/* Logo */}
      <div className="h-12 flex items-center px-4 border-b border-foreground/10 gap-3">
        <Logo size={30} />
        <div className="leading-[14px]">
          <div className="text-foreground/90 text-[11px]">Amethys</div>
          <div className="text-foreground/50 text-[10px]">Wallet</div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-3 space-y-4 overflow-hidden">
        {navItems.map((group) => (
          <div key={group.label} className="space-y-0.5">
            <div className="px-3 mb-1.5 flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <FontAwesomeIcon icon={group.icon} className="w-2.5 h-2.5 text-foreground/40" />
                <span className="text-[9px] font-semibold text-foreground/40 uppercase tracking-wider">{group.label}</span>
              </div>
              {group.collapsible && (
                <FontAwesomeIcon icon={faChevronDown} className="w-2 h-2 text-foreground/30" />
              )}
            </div>
            {group.items.map((item) => (
              <div
                key={item.label}
                className={`flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-[11px] transition-colors ${
                  item.active
                    ? 'text-primary bg-primary/5'
                    : 'text-foreground/60'
                }`}
              >
                <FontAwesomeIcon icon={item.icon} className="w-3 h-3" />
                <span>{item.label}</span>
              </div>
            ))}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-3 pb-3 space-y-0.5 border-t border-foreground/10 pt-3">
        <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-[11px] text-foreground/60">
          <FontAwesomeIcon icon={faGear} className="w-3 h-3" />
          <span>Configurações</span>
        </div>
        <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-[11px] text-foreground/60">
          <FontAwesomeIcon icon={faDiscord} className="w-3 h-3" />
          <span>Suporte no Discord</span>
        </div>
        <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-[11px] text-red-500">
          <FontAwesomeIcon icon={faSignOutAlt} className="w-3 h-3" />
          <span>Encerrar Sessão</span>
        </div>
      </div>
    </div>
  )
}

function Topbar() {
  return (
    <div className="h-12 flex items-center justify-between px-5 border-b border-foreground/10 bg-background">
      {/* Goal progress pill */}
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-foreground/5 border border-foreground/10">
          <FontAwesomeIcon icon={faBullseye} className="w-3 h-3 text-primary" />
          <span className="text-[10px] text-foreground/70">Meta: </span>
          <span className="text-[10px] font-semibold text-foreground">R$ 10.000</span>
          <div className="w-16 h-1 rounded-full bg-foreground/10 overflow-hidden">
            <div className="h-full bg-primary rounded-full" style={{ width: '47%' }} />
          </div>
          <span className="text-[10px] text-foreground/50">47%</span>
        </div>
      </div>

      {/* User menu */}
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center">
          <span className="text-[10px] font-bold text-primary">U</span>
        </div>
        <div className="leading-[13px]">
          <div className="text-[11px] font-semibold text-foreground">Usuário</div>
          <div className="text-[9px] text-foreground/50">Plano FREE</div>
        </div>
        <FontAwesomeIcon icon={faChevronDown} className="w-2.5 h-2.5 text-foreground/40 ml-1" />
      </div>
    </div>
  )
}

function MainContent() {
  const total = SIMULATED_BALANCE
  const intPart = Math.floor(total / 100).toLocaleString('pt-BR')
  const decPart = String(total % 100).padStart(2, '0')

  return (
    <div className="flex-1 overflow-hidden flex flex-col bg-background">
      <Topbar />

      <div className="flex-1 p-4 overflow-hidden space-y-3">
        {/* Header */}
        <div className="border-b border-foreground/10 pb-3 mb-1">
          <div className="flex items-center gap-2">
            <h1 className="text-base font-bold text-foreground">Bom dia, Usuário!</h1>
            <span className="text-sm">☀️</span>
          </div>
          <p className="text-[11px] text-foreground/50 mt-0.5">Visão geral da sua conta e transações</p>
        </div>

        {/* AI input */}
        <div className="relative">
          <div className="w-full pl-3 pr-10 py-2 rounded-xl bg-foreground/5 border border-foreground/10 text-[11px] text-foreground/30">
            Peça para IA que ela faz por você!
          </div>
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <div className="w-5 h-5 rounded-lg bg-foreground/5 flex items-center justify-center">
              <FontAwesomeIcon icon={faArrowRight} className="w-2 h-2 text-foreground/30" />
            </div>
          </div>
        </div>

        {/* Cards row */}
        <div className="grid grid-cols-2 gap-3">
          {/* Balance */}
          <div className="p-4 rounded-xl bg-foreground/5 border border-foreground/10">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-1.5 text-foreground/50">
                <FontAwesomeIcon icon={faWallet} className="w-3 h-3" />
                <span className="text-[10px] font-medium">Saldo Disponível</span>
              </div>
              <FontAwesomeIcon icon={faEye} className="w-3 h-3 text-foreground/30" />
            </div>
            <div className="flex items-baseline mb-3">
              <span className="text-xl font-bold text-foreground">R$ {intPart}</span>
              <span className="text-sm font-bold text-foreground/60">,{decPart}</span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-foreground/10 text-foreground/70 text-[10px] font-medium">
                <FontAwesomeIcon icon={faArrowUp} className="w-2.5 h-2.5" />
                Transferir
              </div>
              <div className="flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-foreground/10 text-foreground/70 text-[10px] font-medium">
                <FontAwesomeIcon icon={faArrowDown} className="w-2.5 h-2.5" />
                Depositar
              </div>
            </div>
          </div>

          {/* Completed transactions */}
          <div className="p-4 rounded-xl bg-foreground/5 border border-foreground/10 flex flex-col justify-between">
            <div className="flex items-center gap-1.5 text-foreground/50 mb-2">
              <FontAwesomeIcon icon={faExchangeAlt} className="w-3 h-3" />
              <span className="text-[10px] font-medium">Transações Completas</span>
            </div>
            <span className="text-xl font-bold text-foreground mb-auto">38</span>
            <div className="flex items-center justify-center gap-1.5 py-1.5 rounded-lg bg-foreground/10 text-foreground/70 text-[10px] font-medium mt-3">
              Ver em detalhes
              <FontAwesomeIcon icon={faArrowRight} className="w-2.5 h-2.5" />
            </div>
          </div>
        </div>

        {/* Transactions */}
        <div className="p-4 rounded-xl bg-foreground/5 border border-foreground/10">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-1.5 text-foreground/50">
              <FontAwesomeIcon icon={faReceipt} className="w-3 h-3" />
              <span className="text-[10px] font-medium">Últimas Transações</span>
            </div>
            <div className="flex items-center gap-1 text-[10px] text-foreground/40">
              Ver todas
              <FontAwesomeIcon icon={faArrowRight} className="w-2 h-2" />
            </div>
          </div>
          <div className="space-y-0">
            {SIMULATED_TRANSACTIONS.map((tx, idx) => (
              <div
                key={tx.id}
                className={`flex items-center gap-3 py-2.5 ${idx < SIMULATED_TRANSACTIONS.length - 1 ? 'border-b border-foreground/5' : ''}`}
              >
                <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${tx.type === 'received' ? 'bg-green-500/10' : 'bg-red-500/10'}`}>
                  <FontAwesomeIcon
                    icon={tx.type === 'received' ? faArrowDown : faArrowUp}
                    className={`w-3 h-3 ${tx.type === 'received' ? 'text-green-500' : 'text-red-500'}`}
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[10px] font-medium text-foreground truncate">{tx.label}</p>
                  <p className="text-[9px] text-foreground/40">{tx.date}</p>
                </div>
                <p className={`text-[10px] font-bold flex-shrink-0 ${tx.type === 'received' ? 'text-green-500' : 'text-red-500'}`}>
                  {tx.type === 'received' ? '+' : '-'}R$ {(tx.amount / 100).toFixed(2).replace('.', ',')}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export function DashboardPreview() {
  const containerRef = useRef<HTMLDivElement>(null)

  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const mouseXSpring = useSpring(x, { stiffness: 500, damping: 100 })
  const mouseYSpring = useSpring(y, { stiffness: 500, damping: 100 })
  const rotateX = useTransform(mouseYSpring, [-0.5, 0.5], ['7.5deg', '-7.5deg'])
  const rotateY = useTransform(mouseXSpring, [-0.5, 0.5], ['-7.5deg', '7.5deg'])

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current) return
    const rect = containerRef.current.getBoundingClientRect()
    x.set((e.clientX - rect.left) / rect.width - 0.5)
    y.set((e.clientY - rect.top) / rect.height - 0.5)
  }

  const handleMouseLeave = () => {
    x.set(0)
    y.set(0)
  }

  return (
    <motion.section
      initial={{ opacity: 0, y: 40 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, delay: 1.3, ease: 'easeOut' }}
      className="relative z-20 w-full max-w-[1200px] self-center mt-8 md:mt-24 mb-4 md:mb-8 mx-auto"
    >
      <motion.div
        ref={containerRef}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        initial={{ opacity: 0, scale: 0.9, y: 30 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.9, delay: 1.5, ease: [0.25, 0.46, 0.45, 0.94] }}
        style={{
          rotateX,
          rotateY,
          transformStyle: 'preserve-3d',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(128, 128, 128, 0.15)',
          perspective: '1000px',
        }}
        className="relative rounded-2xl overflow-hidden bg-background border border-neutral-700/30 shadow-2xl cursor-pointer w-full"
      >
        {/* Edge gradients */}
        <div className="absolute inset-0 bg-gradient-to-t from-background/80 via-transparent to-transparent z-10 pointer-events-none" />
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-background/60 z-10 pointer-events-none" />
        <div className="absolute inset-0 bg-gradient-to-r from-background/40 via-transparent to-background/40 z-10 pointer-events-none" />

        {/* Top fade */}
        <div className="absolute top-0 left-0 right-0 h-8 bg-gradient-to-b from-background to-transparent z-10 pointer-events-none" />
        {/* Bottom fade */}
        <div className="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-background to-transparent z-10 pointer-events-none" />

        {/* Dashboard UI */}
        <div className="flex h-[520px] overflow-hidden select-none">
          <Sidebar />
          <MainContent />
        </div>
      </motion.div>
    </motion.section>
  )
}
