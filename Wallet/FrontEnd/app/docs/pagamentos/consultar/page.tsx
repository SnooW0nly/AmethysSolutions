'use client'

import { DocPageHeader, EndpointBar, ParamsTable, Callout } from '@/components/docs/doc-components'

const statusList = [
  { status: 'PENDING', meaning: 'Aguardando pagamento do PIX' },
  { status: 'COMPLETED', meaning: 'PIX recebido e saldo creditado' },
  { status: 'EXPIRED', meaning: 'QR Code expirado sem pagamento' },
]

export default function PagamentoConsultarPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <DocPageHeader
        badge="Pagamentos PIX"
        title="Consultar cobrança"
        description="Busca os detalhes de uma cobrança pelo ID. Útil para polling de status após criação."
      />

      <EndpointBar method="GET" path="/payment/get/:id" auth />

      <div className="mb-6">
        <h3 className="text-[13px] font-semibold text-foreground/60 uppercase tracking-wider mb-3 font-mono">Parâmetros de rota</h3>
        <ParamsTable
          columns={['Parâmetro', 'Tipo', 'Descrição']}
          params={[
            { name: 'id', type: 'string', description: <>ID da cobrança retornado em <code className="font-mono text-[11px] text-primary">/payment/create</code></> },
          ]}
        />
      </div>

      <Callout type="warn">
        Não utilize este endpoint para confirmar pagamentos em produção. O status é atualizado de forma segura pelo sistema interno.
        Use <strong>webhooks</strong> para confirmação confiável.
      </Callout>

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
