'use client'

import { DocPageHeader, EndpointBar, ParamsTable } from '@/components/docs/doc-components'

export default function SaquesListarPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <DocPageHeader
        badge="Saques"
        title="Listar saques"
        description="Lista todos os saques da conta autenticada com suporte a filtros e paginação."
      />

      <EndpointBar method="GET" path="/withdraw/list" auth />

      <ParamsTable
        columns={['Query param', 'Tipo', 'Padrão', 'Descrição']}
        params={[
          { name: 'status', type: 'string', description: 'Filtrar por status' },
          { name: 'limit', type: 'integer', default: '50', description: 'Itens por página' },
          { name: 'offset', type: 'integer', default: '0', description: 'Deslocamento para paginação' },
        ]}
      />
    </div>
  )
}
