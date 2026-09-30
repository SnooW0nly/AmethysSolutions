'use client'

import { DocPageHeader, EndpointBar, ParamsTable, CodeBlock, Grid2, Callout } from '@/components/docs/doc-components'

export default function PagamentoCriarPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <DocPageHeader
        badge="Pagamentos PIX"
        title="Criar cobrança PIX"
        description="Gera um QR Code PIX para receber pagamento. A taxa de serviço é deduzida automaticamente do valor recebido. Limite de R$ 1.000,00 por transação."
      />

      <EndpointBar method="POST" path="/payment/create" auth />

      <div className="mb-6">
        <h3 className="text-[13px] font-semibold text-foreground/60 uppercase tracking-wider mb-3 font-mono">Parâmetros do body</h3>
        <ParamsTable params={[
          { name: 'value', type: 'number', required: true, description: <>Valor em reais. Ex: <code className="font-mono text-[11px] text-primary">100</code> = R$ 100,00. Mínimo: R$ 1,00</> },
          { name: 'description', type: 'string', required: false, description: 'Descrição interna da cobrança' },
          { name: 'coverFee', type: 'boolean', required: false, description: <>Se <code className="font-mono text-[11px] text-primary">true</code>, o valor informado é o líquido desejado e a taxa é adicionada ao QR Code</> },
          { name: 'splitUser', type: 'string', required: false, description: 'E-mail de outro usuário para dividir o pagamento' },
          { name: 'splitTax', type: 'number', required: false, description: <>Porcentagem (0.01–100) enviada ao <code className="font-mono text-[11px] text-primary">splitUser</code></> },
        ]} />
      </div>

      <Callout type="info">
        <strong>coverFee</strong>: por padrão, o <code className="font-mono text-[12px]">value</code> é o total do QR Code (taxa é descontada na chegada).
        Com <code className="font-mono text-[12px]">coverFee: true</code>, o <code className="font-mono text-[12px]">value</code> é o que você recebe líquido e a taxa é somada ao QR Code.
      </Callout>

      <Grid2>
        <CodeBlock lang="request">{`curl -X POST https://api.amethys.lat/api/v1/payment/create \\
  -H <span style="color:#86efac">"X-API-Key: vp_sua_key"</span> \\
  -H <span style="color:#86efac">"Content-Type: application/json"</span> \\
  -d '{
    <span style="color:#93c5fd">"value"</span>: <span style="color:#fde68a">100</span>,
    <span style="color:#93c5fd">"description"</span>: <span style="color:#86efac">"Pedido #1234"</span>,
    <span style="color:#93c5fd">"coverFee"</span>: <span style="color:#f0abfc">false</span>
  }'`}</CodeBlock>
        <CodeBlock lang="response 201" copyable={false}>{`{
  <span style="color:#93c5fd">"success"</span>: <span style="color:#f0abfc">true</span>,
  <span style="color:#93c5fd">"message"</span>: <span style="color:#86efac">"Transação criada com sucesso"</span>,
  <span style="color:#93c5fd">"data"</span>: {
    <span style="color:#93c5fd">"id"</span>: <span style="color:#86efac">"pay_xyz789"</span>,
    <span style="color:#93c5fd">"transactionId"</span>: <span style="color:#86efac">"txn_mistic_123"</span>,
    <span style="color:#93c5fd">"value"</span>: <span style="color:#fde68a">10000</span>,
    <span style="color:#93c5fd">"netValue"</span>: <span style="color:#fde68a">9950</span>,
    <span style="color:#93c5fd">"fee"</span>: <span style="color:#fde68a">50</span>,
    <span style="color:#93c5fd">"status"</span>: <span style="color:#86efac">"PENDING"</span>,
    <span style="color:#93c5fd">"qrcodeUrl"</span>: <span style="color:#86efac">"data:image/png;base64,..."</span>,
    <span style="color:#93c5fd">"copyPaste"</span>: <span style="color:#86efac">"00020126..."</span>,
    <span style="color:#93c5fd">"createdAt"</span>: <span style="color:#86efac">"2025-05-14T10:00:00.000Z"</span>
  }
}`}</CodeBlock>
      </Grid2>
    </div>
  )
}
