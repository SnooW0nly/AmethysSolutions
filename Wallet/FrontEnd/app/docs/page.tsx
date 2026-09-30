'use client'

import Link from 'next/link'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faBook, faUser, faMoneyBillTransfer, faArrowDown,
  faArrowsLeftRight, faUserGroup, faChartBar, faChevronRight,
  faKey, faCode, faWebhook, faShieldHalved
} from '@fortawesome/free-solid-svg-icons'
import { QuickRefCard } from '@/components/docs/doc-components'

const quickRef = [
  { method: 'POST', path: '/user/register', description: 'Criar nova conta', href: '/docs/usuario/registrar' },
  { method: 'POST', path: '/payment/create', description: 'Gerar cobrança PIX', href: '/docs/pagamentos/criar' },
  { method: 'POST', path: '/withdraw/create', description: 'Sacar via PIX', href: '/docs/saques/pix' },
  { method: 'POST', path: '/transfer/internal', description: 'Transferência interna', href: '/docs/transferencias/interna' },
  { method: 'GET',  path: '/user/balance', description: 'Consultar saldo', href: '/docs/usuario/saldo' },
  { method: 'GET',  path: '/payment/list', description: 'Listar cobranças', href: '/docs/pagamentos/listar' },
  { method: 'GET',  path: '/public-stats', description: 'Estatísticas públicas', href: '/docs/publico/estatisticas' },
  { method: 'POST', path: '/withdraw/crypto', description: 'Sacar em USDT BEP20', href: '/docs/saques/crypto' },
]

const sections = [
  {
    icon: faBook,
    label: 'Introdução',
    description: 'Autenticação, rate limits, erros e webhooks',
    href: '/docs/introducao/visao-geral',
    color: 'text-violet-400 bg-violet-500/10',
  },
  {
    icon: faUser,
    label: 'Usuário',
    description: 'Registro, dados, saldo e histórico',
    href: '/docs/usuario/registrar',
    color: 'text-blue-400 bg-blue-500/10',
  },
  {
    icon: faMoneyBillTransfer,
    label: 'Pagamentos PIX',
    description: 'Cobranças, consultas e envio de PIX',
    href: '/docs/pagamentos/criar',
    color: 'text-emerald-400 bg-emerald-500/10',
  },
  {
    icon: faArrowDown,
    label: 'Saques',
    description: 'Saque via PIX ou criptomoedas',
    href: '/docs/saques/pix',
    color: 'text-amber-400 bg-amber-500/10',
  },
  {
    icon: faArrowsLeftRight,
    label: 'Transferências',
    description: 'Transferências internas gratuitas',
    href: '/docs/transferencias/interna',
    color: 'text-cyan-400 bg-cyan-500/10',
  },
  {
    icon: faUserGroup,
    label: 'Afiliados',
    description: 'Programa de indicação e comissões',
    href: '/docs/afiliados/registrar',
    color: 'text-pink-400 bg-pink-500/10',
  },
]

export default function DocsPage() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-10 md:py-14">
      {/* Hero */}
      <div className="mb-12 pb-10 border-b border-foreground/10">
        <div className="inline-flex items-center gap-2 text-[11px] font-mono text-foreground/40 bg-foreground/5 border border-foreground/10 px-3 py-1.5 rounded-full mb-5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          REST API — Versão 1.0
        </div>
        <h1 className="text-4xl md:text-5xl font-bold text-foreground mb-4 leading-tight">
          Amethys Wallet<br />
          <span className="text-primary">API Reference</span>
        </h1>
        <p className="text-[15px] text-foreground/50 leading-relaxed max-w-2xl mb-8">
          API completa para integrar pagamentos PIX, saques, transferências internas e programa de afiliados na sua aplicação.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            { label: 'Base URL', value: 'api.amethys.lat/api/v1' },
            { label: 'Autenticação', value: 'X-API-Key: vp_...' },
            { label: 'Formato', value: 'application/json' },
          ].map(item => (
            <div key={item.label} className="bg-foreground/[0.03] border border-foreground/10 rounded-xl px-4 py-3.5">
              <div className="text-[10px] font-semibold text-foreground/30 uppercase tracking-wider mb-1.5">{item.label}</div>
              <code className="font-mono text-[12px] text-primary">{item.value}</code>
            </div>
          ))}
        </div>
      </div>

      {/* Sections grid */}
      <div className="mb-12">
        <h2 className="text-[18px] font-semibold text-foreground mb-5">Explore a documentação</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
          {sections.map(section => (
            <Link
              key={section.label}
              href={section.href}
              className="group flex flex-col gap-3 p-5 bg-foreground/[0.03] border border-foreground/10 rounded-xl hover:border-foreground/20 hover:bg-foreground/[0.05] transition-all"
            >
              <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${section.color}`}>
                <FontAwesomeIcon icon={section.icon} className="w-4 h-4" />
              </div>
              <div>
                <div className="text-[14px] font-semibold text-foreground mb-1 group-hover:text-primary transition-colors">{section.label}</div>
                <div className="text-[12px] text-foreground/40 leading-relaxed">{section.description}</div>
              </div>
              <FontAwesomeIcon icon={faChevronRight} className="w-3 h-3 text-foreground/20 group-hover:text-primary group-hover:translate-x-0.5 transition-all mt-auto self-start" />
            </Link>
          ))}
        </div>
      </div>

      {/* Quick reference */}
      <div className="mb-12">
        <h2 className="text-[18px] font-semibold text-foreground mb-2">Referência rápida</h2>
        <p className="text-[13px] text-foreground/40 mb-5">Todos os endpoints disponíveis de um relance.</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
          {quickRef.map(item => (
            <QuickRefCard key={item.path} {...item} />
          ))}
        </div>
      </div>

      {/* Getting started callout */}
      <div className="bg-primary/5 border border-primary/20 rounded-xl p-6 flex gap-4 items-start">
        <div className="w-10 h-10 rounded-lg bg-primary/15 flex items-center justify-center flex-shrink-0">
          <FontAwesomeIcon icon={faKey} className="w-4 h-4 text-primary" />
        </div>
        <div>
          <h3 className="text-[15px] font-semibold text-foreground mb-1.5">Começar em 2 passos</h3>
          <p className="text-[13px] text-foreground/50 mb-3 leading-relaxed">
            Registre uma conta via API e sua <code className="font-mono text-primary text-[12px]">vp_api_key</code> será gerada automaticamente. Use-a em todo o cabeçalho das requisições.
          </p>
          <Link
            href="/docs/introducao/visao-geral"
            className="inline-flex items-center gap-2 text-[13px] font-medium text-primary hover:text-primary/80 transition-colors"
          >
            Ver guia de início
            <FontAwesomeIcon icon={faChevronRight} className="w-3 h-3" />
          </Link>
        </div>
      </div>
    </div>
  )
}
