'use client'

import { DocPageHeader, EndpointBar, ParamsTable } from '@/components/docs/doc-components'

const statusList = [
  { status: 'PENDING', meaning: 'Aguardando processamento' },
  { status: 'PROCESSING', meaning: 'Em processamento na gateway' },
  { status: 'COMPLETED', meaning: 'PIX enviado com sucesso' },
  { status: 'FAILED', meaning: 'Saque falhou — saldo não debitado' },
]

export function SaquesConsultarPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <DocPageHeader
        badge="Saques"
        title="Consultar saque"
        description="Busca os detalhes de um saque pelo ID, incluindo status de processamento."
      />

      <EndpointBar method="GET" path="/withdraw/get/:id" auth />

      <div className="mb-6">
        <h3 className="text-[13px] font-semibold text-foreground/60 uppercase tracking-wider mb-3 font-mono">Status possíveis</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-[13px] border-collapse">
            <thead>
              <tr className="border-b border-foreground/10">
                {['Status', 'Significado'].map(col => (
                  <th key={col} className="text-left py-2.5 px-3 text-[10px] font-semibold text-foreground/30 uppercase tracking-wider font-mono">{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {statusList.map(({ status, meaning }) => (
                <tr key={status} className="border-b border-foreground/[0.06] last:border-0 hover:bg-foreground/[0.02]">
                  <td className="py-3 px-3 font-mono text-[12px] text-primary">{status}</td>
                  <td className="py-3 px-3 text-foreground/50">{meaning}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default SaquesConsultarPage
