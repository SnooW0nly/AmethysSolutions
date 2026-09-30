'use client'

import { DocPageHeader, EndpointBar, ParamsTable, CodeBlock, Grid2, Callout } from '@/components/docs/doc-components'

export default function TransferenciasInternaPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <DocPageHeader
        badge="Transferências"
        title="Transferência Interna"
        description="Transfira saldo entre contas Amethys Wallet instantaneamente, sem taxa e sem limites definidos."
      />

      <EndpointBar method="POST" path="/transfer/internal" auth />

      <div className="mb-6">
        <h3 className="text-[13px] font-semibold text-foreground/60 uppercase tracking-wider mb-3 font-mono">Parâmetros do body</h3>
        <ParamsTable params={[
          { name: 'email', type: 'string', required: true, description: 'E-mail da conta Amethys de destino' },
          { name: 'amount', type: 'number', required: true, description: 'Valor em reais a transferir' },
          { name: 'description', type: 'string', required: false, description: 'Descrição da transferência' },
        ]} />
      </div>

      <Callout type="info">
        Transferências internas são <strong>instantâneas e sem custo</strong>.
        O destinatário deve ser um usuário Amethys ativo.
        Não é possível transferir para si mesmo.
      </Callout>

      <Grid2>
        <CodeBlock lang="request">{`curl -X POST https://api.amethys.lat/api/v1/transfer/internal \\
  -H <span style="color:#86efac">"X-API-Key: vp_sua_key"</span> \\
  -H <span style="color:#86efac">"Content-Type: application/json"</span> \\
  -d '{
    <span style="color:#93c5fd">"email"</span>: <span style="color:#86efac">"parceiro@empresa.com"</span>,
    <span style="color:#93c5fd">"amount"</span>: <span style="color:#fde68a">500</span>,
    <span style="color:#93c5fd">"description"</span>: <span style="color:#86efac">"Comissão mensal"</span>
  }'`}</CodeBlock>
        <CodeBlock lang="response 201" copyable={false}>{`{
  <span style="color:#93c5fd">"success"</span>: <span style="color:#f0abfc">true</span>,
  <span style="color:#93c5fd">"message"</span>: <span style="color:#86efac">"Transferência realizada com sucesso"</span>,
  <span style="color:#93c5fd">"data"</span>: {
    <span style="color:#93c5fd">"id"</span>: <span style="color:#86efac">"trf_def789"</span>,
    <span style="color:#93c5fd">"amount"</span>: <span style="color:#fde68a">50000</span>,
    <span style="color:#93c5fd">"recipientEmail"</span>: <span style="color:#86efac">"parceiro@empresa.com"</span>,
    <span style="color:#93c5fd">"status"</span>: <span style="color:#86efac">"COMPLETED"</span>,
    <span style="color:#93c5fd">"createdAt"</span>: <span style="color:#86efac">"2025-05-14T12:00:00.000Z"</span>
  }
}`}</CodeBlock>
      </Grid2>
    </div>
  )
}
