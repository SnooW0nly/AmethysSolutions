'use client'

import { DocPageHeader, ParamsTable, Callout, StatusBadge } from '@/components/docs/doc-components'

export default function RateLimitsPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <DocPageHeader
        badge="Introdução"
        title="Rate Limits"
        description="A API possui limites de requisições por minuto baseados no tipo de autenticação. Requisições com API Key possuem limites mais permissivos."
      />

      <div className="overflow-x-auto mb-6">
        <table className="w-full text-[13px] border-collapse">
          <thead>
            <tr className="border-b border-foreground/10">
              {['Tipo de endpoint', 'JWT (login)', 'API Key'].map(col => (
                <th key={col} className="text-left py-2.5 px-3 text-[10px] font-semibold text-foreground/30 uppercase tracking-wider font-mono">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[
              ['Default (leitura)', '60 req/min', '100 req/min'],
              ['Payment (criação)', '20 req/min', '30 req/min'],
              ['Strict (saque, transferência)', '30 req/min', '50 req/min'],
              ['Público (sem auth)', '10 req/min', '10 req/min'],
            ].map(([type, jwt, key], i) => (
              <tr key={i} className="border-b border-foreground/[0.06] last:border-0 hover:bg-foreground/[0.02] transition-colors">
                <td className="py-3 px-3 font-mono text-[12px] text-foreground/80">{type}</td>
                <td className="py-3 px-3 text-foreground/50">{jwt}</td>
                <td className="py-3 px-3 text-foreground/50">{key === '10 req/min' ? <span className="text-foreground/30 italic">compartilhado</span> : key}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Callout type="info">
        Ao atingir o limite, a API retorna <strong>HTTP 429</strong>.
        Implemente exponential backoff na sua integração.
      </Callout>
    </div>
  )
}
