'use client'

import { useState, ReactNode } from 'react'
import Link from 'next/link'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faCopy, faCheck, faLock, faChevronRight,
  faInfoCircle, faTriangleExclamation, faBolt
} from '@fortawesome/free-solid-svg-icons'

// ── Method badge ─────────────────────────────────────────────────────────────
const methodStyles: Record<string, string> = {
  GET:    'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20',
  POST:   'bg-blue-500/15 text-blue-400 border border-blue-500/20',
  PUT:    'bg-amber-500/15 text-amber-400 border border-amber-500/20',
  DELETE: 'bg-red-500/15 text-red-400 border border-red-500/20',
}

export function MethodBadge({ method }: { method: string }) {
  return (
    <span className={`inline-flex items-center font-mono text-[11px] font-bold px-2 py-0.5 rounded ${methodStyles[method] || 'bg-foreground/10 text-foreground/60'}`}>
      {method}
    </span>
  )
}

// ── Endpoint bar ─────────────────────────────────────────────────────────────
export function EndpointBar({ method, path, auth }: { method: string; path: string; auth?: boolean }) {
  return (
    <div className="flex items-center overflow-hidden rounded-lg border border-foreground/10 mb-5 font-mono text-[13px]">
      <span className={`px-3 py-2.5 text-[11px] font-bold tracking-wider flex-shrink-0 ${methodStyles[method]}`}>
        {method}
      </span>
      <span className="px-4 py-2.5 text-foreground/80 flex-1 bg-foreground/[0.03] border-l border-foreground/10 overflow-x-auto whitespace-nowrap">
        {path}
      </span>
      {auth && (
        <span className="flex items-center gap-1.5 px-3 py-2.5 text-[11px] text-violet-400 bg-violet-500/10 border-l border-foreground/10 flex-shrink-0">
          <FontAwesomeIcon icon={faLock} className="w-3 h-3" />
          API Key
        </span>
      )}
    </div>
  )
}

// ── Code block ───────────────────────────────────────────────────────────────
export function CodeBlock({ lang, children, copyable = true }: { lang: string; children: string; copyable?: boolean }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(children.trim())
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="rounded-xl overflow-hidden border border-foreground/10 mb-5">
      <div className="flex items-center justify-between px-4 py-2.5 bg-foreground/[0.04] border-b border-foreground/10">
        <span className="text-[10px] font-mono font-semibold text-foreground/30 uppercase tracking-wider">{lang}</span>
        {copyable && (
          <button
            onClick={handleCopy}
            className={`flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 rounded border transition-all ${
              copied
                ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
                : 'text-foreground/30 border-foreground/10 hover:text-foreground/60 hover:border-foreground/20'
            }`}
          >
            <FontAwesomeIcon icon={copied ? faCheck : faCopy} className="w-3 h-3" />
            {copied ? 'Copiado!' : 'Copiar'}
          </button>
        )}
      </div>
      <div className="p-5 bg-[#0c0d0e] overflow-x-auto">
        <pre
          className="font-mono text-[12.5px] leading-relaxed text-foreground/70 whitespace-pre"
          dangerouslySetInnerHTML={{ __html: children }}
        />
      </div>
    </div>
  )
}

// ── Params table ─────────────────────────────────────────────────────────────
interface Param {
  name: string
  type: string
  required?: boolean
  default?: string
  description: ReactNode
}

export function ParamsTable({ params, columns = ['Campo', 'Tipo', 'Req.', 'Descrição'] }: { params: Param[]; columns?: string[] }) {
  return (
    <div className="overflow-x-auto mb-5">
      <table className="w-full text-[13px] border-collapse">
        <thead>
          <tr className="border-b border-foreground/10">
            {columns.map(col => (
              <th key={col} className="text-left py-2.5 px-3 text-[10px] font-semibold text-foreground/30 uppercase tracking-wider font-mono">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {params.map((param, i) => (
            <tr key={i} className="border-b border-foreground/[0.06] last:border-0 hover:bg-foreground/[0.02] transition-colors">
              <td className="py-3 px-3 font-mono text-[12px] text-foreground/90">{param.name}</td>
              <td className="py-3 px-3">
                <span className="font-mono text-[11px] text-violet-400 bg-violet-500/10 px-1.5 py-0.5 rounded">{param.type}</span>
              </td>
              {columns.length > 3 && (
                <td className="py-3 px-3">
                  {param.required !== undefined ? (
                    <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${param.required ? 'bg-red-500/10 text-red-400' : 'bg-foreground/10 text-foreground/40'}`}>
                      {param.required ? 'Required' : 'Optional'}
                    </span>
                  ) : param.default ? (
                    <code className="font-mono text-[11px] text-foreground/40">{param.default}</code>
                  ) : <span className="text-foreground/20">—</span>}
                </td>
              )}
              <td className="py-3 px-3 text-foreground/60 leading-relaxed">{param.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Callout ──────────────────────────────────────────────────────────────────
const calloutStyles = {
  info:    { bg: 'bg-blue-500/5 border-blue-500/20', icon: faInfoCircle, iconColor: 'text-blue-400' },
  warn:    { bg: 'bg-amber-500/5 border-amber-500/20', icon: faTriangleExclamation, iconColor: 'text-amber-400' },
  danger:  { bg: 'bg-red-500/5 border-red-500/20', icon: faBolt, iconColor: 'text-red-400' },
}

export function Callout({ type, children }: { type: 'info' | 'warn' | 'danger'; children: ReactNode }) {
  const s = calloutStyles[type]
  return (
    <div className={`flex gap-3 p-4 rounded-xl border mb-5 ${s.bg}`}>
      <FontAwesomeIcon icon={s.icon} className={`w-4 h-4 flex-shrink-0 mt-0.5 ${s.iconColor}`} />
      <div className="text-[13.5px] text-foreground/70 leading-relaxed">{children}</div>
    </div>
  )
}

// ── Response group ───────────────────────────────────────────────────────────
const statusStyles: Record<string, string> = {
  '200': 'bg-emerald-500/10 text-emerald-400',
  '201': 'bg-emerald-500/10 text-emerald-400',
  '400': 'bg-amber-500/10 text-amber-400',
  '401': 'bg-red-500/10 text-red-400',
  '404': 'bg-foreground/10 text-foreground/50',
  '429': 'bg-red-500/10 text-red-400',
  '500': 'bg-red-500/10 text-red-400',
}

export function StatusBadge({ code }: { code: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 font-mono text-[11px] font-bold px-2 py-0.5 rounded ${statusStyles[code] || 'bg-foreground/10 text-foreground/50'}`}>
      {code}
    </span>
  )
}

// ── Grid 2 columns ────────────────────────────────────────────────────────────
export function Grid2({ children }: { children: ReactNode }) {
  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mb-2">
      {children}
    </div>
  )
}

// ── Section wrapper ───────────────────────────────────────────────────────────
export function DocSection({ id, title, description, children }: {
  id?: string
  title?: string
  description?: string
  children: ReactNode
}) {
  return (
    <div id={id} className="scroll-mt-20 mb-12">
      {title && (
        <h3 className="text-[17px] font-semibold text-foreground mb-1.5 flex items-center gap-2 mt-8 first:mt-0">
          {title}
          {id && (
            <a href={`#${id}`} className="text-foreground/20 hover:text-foreground/50 text-[13px] transition-colors">#</a>
          )}
        </h3>
      )}
      {description && <p className="text-[14px] text-foreground/50 mb-5 leading-relaxed">{description}</p>}
      {children}
    </div>
  )
}

// ── Page header ───────────────────────────────────────────────────────────────
export function DocPageHeader({ title, description, badge }: { title: string; description: string; badge?: string }) {
  return (
    <div className="border-b border-foreground/10 pb-8 mb-8">
      {badge && (
        <div className="inline-flex items-center gap-2 text-[11px] font-mono text-foreground/40 bg-foreground/5 border border-foreground/10 px-2.5 py-1 rounded-full mb-4">
          <span className="w-1.5 h-1.5 rounded-full bg-primary/60" />
          {badge}
        </div>
      )}
      <h1 className="text-[28px] md:text-[32px] font-bold text-foreground mb-3 leading-tight">{title}</h1>
      <p className="text-[15px] text-foreground/50 leading-relaxed max-w-2xl">{description}</p>
    </div>
  )
}

// ── Quick ref link ────────────────────────────────────────────────────────────
export function QuickRefCard({ method, path, description, href }: { method: string; path: string; description: string; href: string }) {
  return (
    <Link
      href={href}
      className="group flex flex-col gap-2 p-4 bg-foreground/[0.03] border border-foreground/10 rounded-xl hover:border-foreground/20 hover:bg-foreground/[0.05] transition-all"
    >
      <MethodBadge method={method} />
      <span className="font-mono text-[12px] text-foreground/80 group-hover:text-foreground transition-colors">{path}</span>
      <span className="text-[12px] text-foreground/40">{description}</span>
    </Link>
  )
}

// ── Tabs ─────────────────────────────────────────────────────────────────────
export function Tabs({ tabs, children }: { tabs: string[]; children: (active: string) => ReactNode }) {
  const [active, setActive] = useState(tabs[0])
  return (
    <div className="mb-5">
      <div className="flex gap-0 mb-0 relative z-10">
        {tabs.map(tab => (
          <button
            key={tab}
            onClick={() => setActive(tab)}
            className={`px-4 py-2 text-[12px] font-mono rounded-t-lg border border-b-0 transition-all ${
              active === tab
                ? 'text-foreground bg-[#0c0d0e] border-foreground/10'
                : 'text-foreground/40 bg-transparent border-transparent hover:text-foreground/60'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>
      <div className="rounded-b-xl rounded-tr-xl overflow-hidden border border-foreground/10">
        {children(active)}
      </div>
    </div>
  )
}
