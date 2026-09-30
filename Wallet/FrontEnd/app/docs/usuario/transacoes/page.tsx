'use client'

import { DocPageHeader, EndpointBar, ParamsTable, CodeBlock } from '@/components/docs/doc-components'

export default function UsuarioTransacoesPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <DocPageHeader
        badge="Usuário"
        title="Listar transações"
        description="Retorna o histórico completo de transações: entradas (PIX recebido), saídas (saques, PIX enviados) e transferências internas. Suporta paginação e filtros."
      />

      <EndpointBar method="GET" path="/user/transactions" auth />

      <div className="mb-6">
        <h3 className="text-[13px] font-semibold text-foreground/60 uppercase tracking-wider mb-3 font-mono">Query parameters</h3>
        <ParamsTable
          columns={['Parâmetro', 'Tipo', 'Padrão', 'Descrição']}
          params={[
            { name: 'page', type: 'integer', default: '1', description: 'Número da página' },
            { name: 'limit', type: 'integer', default: '50', description: 'Itens por página (máx. 1000)' },
            { name: 'type', type: 'string', description: <><code className="font-mono text-[11px] text-primary">income</code>, <code className="font-mono text-[11px] text-primary">expense</code> ou <code className="font-mono text-[11px] text-primary">transfer</code></> },
            { name: 'status', type: 'string', description: <><code className="font-mono text-[11px] text-primary">COMPLETED</code>, <code className="font-mono text-[11px] text-primary">PENDING</code>, <code className="font-mono text-[11px] text-primary">FAILED</code></> },
          ]}
        />
      </div>

      <CodeBlock lang="response 200" copyable={false}>{`{
  <span style="color:#93c5fd">"success"</span>: <span style="color:#f0abfc">true</span>,
  <span style="color:#93c5fd">"data"</span>: {
    <span style="color:#93c5fd">"transactions"</span>: [
      {
        <span style="color:#93c5fd">"id"</span>: <span style="color:#86efac">"pay_abc123"</span>,
        <span style="color:#93c5fd">"type"</span>: <span style="color:#86efac">"income"</span>,
        <span style="color:#93c5fd">"transactionType"</span>: <span style="color:#86efac">"payment"</span>,
        <span style="color:#93c5fd">"amount"</span>: <span style="color:#fde68a">9950</span>,
        <span style="color:#93c5fd">"status"</span>: <span style="color:#86efac">"COMPLETED"</span>,
        <span style="color:#93c5fd">"description"</span>: <span style="color:#86efac">"Pagamento recebido"</span>,
        <span style="color:#93c5fd">"date"</span>: <span style="color:#86efac">"2025-05-14T10:30:00.000Z"</span>
      }
    ],
    <span style="color:#93c5fd">"pagination"</span>: {
      <span style="color:#93c5fd">"total"</span>: <span style="color:#fde68a">42</span>,
      <span style="color:#93c5fd">"page"</span>: <span style="color:#fde68a">1</span>,
      <span style="color:#93c5fd">"limit"</span>: <span style="color:#fde68a">50</span>,
      <span style="color:#93c5fd">"hasMore"</span>: <span style="color:#f0abfc">false</span>
    }
  }
}`}</CodeBlock>
    </div>
  )
}
