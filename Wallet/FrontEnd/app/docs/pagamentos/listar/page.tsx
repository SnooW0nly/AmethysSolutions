'use client'

import { DocPageHeader, EndpointBar, ParamsTable } from '@/components/docs/doc-components'

export default function PagamentoListarPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <DocPageHeader
        badge="Pagamentos PIX"
        title="Listar cobranças"
        description="Lista todas as cobranças PIX da conta autenticada com paginação e estatísticas."
      />

      <EndpointBar method="GET" path="/payment/list" auth />

      <ParamsTable
        columns={['Query param', 'Tipo', 'Padrão', 'Descrição']}
        params={[
          { name: 'status', type: 'string', description: <><code className="font-mono text-[11px] text-primary">PENDING</code>, <code className="font-mono text-[11px] text-primary">COMPLETED</code></> },
          { name: 'limit', type: 'integer', default: '50', description: 'Itens por página' },
          { name: 'offset', type: 'integer', default: '0', description: 'Deslocamento para paginação' },
        ]}
      />
    </div>
  )
}
