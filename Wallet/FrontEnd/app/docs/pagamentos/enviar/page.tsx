'use client'

import { DocPageHeader, EndpointBar, ParamsTable, CodeBlock, Grid2, Callout } from '@/components/docs/doc-components'

export default function PagamentoEnviarPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <DocPageHeader
        badge="Pagamentos PIX"
        title="Enviar PIX"
        description="Envia um PIX para qualquer chave PIX usando o saldo disponível na conta. Exclusivo para API Key — não funciona com JWT."
      />

      <EndpointBar method="POST" path="/payment/send" auth />

      <Callout type="danger">
        <strong>Operação irreversível.</strong> O saldo é debitado imediatamente antes do envio.
        Se a transferência falhar, o saldo é estornado automaticamente.
      </Callout>

      <div className="mb-6">
        <h3 className="text-[13px] font-semibold text-foreground/60 uppercase tracking-wider mb-3 font-mono">Parâmetros do body</h3>
        <ParamsTable params={[
          { name: 'amount', type: 'number', required: true, description: 'Valor em reais a enviar. Taxa é descontada do total.' },
          { name: 'pixKey', type: 'string', required: true, description: 'Chave PIX do destinatário' },
          { name: 'pixKeyType', type: 'string', required: true, description: <><code className="font-mono text-[11px] text-primary">CPF</code>, <code className="font-mono text-[11px] text-primary">CNPJ</code>, <code className="font-mono text-[11px] text-primary">EMAIL</code>, <code className="font-mono text-[11px] text-primary">PHONE</code>, <code className="font-mono text-[11px] text-primary">RANDOM</code></> },
          { name: 'description', type: 'string', required: false, description: 'Descrição interna do envio' },
        ]} />
      </div>

      <Grid2>
        <CodeBlock lang="request">{`curl -X POST https://api.amethys.lat/api/v1/payment/send \\
  -H <span style="color:#86efac">"X-API-Key: vp_sua_key"</span> \\
  -H <span style="color:#86efac">"Content-Type: application/json"</span> \\
  -d '{
    <span style="color:#93c5fd">"amount"</span>: <span style="color:#fde68a">50</span>,
    <span style="color:#93c5fd">"pixKey"</span>: <span style="color:#86efac">"cliente@email.com"</span>,
    <span style="color:#93c5fd">"pixKeyType"</span>: <span style="color:#86efac">"EMAIL"</span>,
    <span style="color:#93c5fd">"description"</span>: <span style="color:#86efac">"Reembolso pedido #99"</span>
  }'`}</CodeBlock>
        <CodeBlock lang="response 200" copyable={false}>{`{
  <span style="color:#93c5fd">"success"</span>: <span style="color:#f0abfc">true</span>,
  <span style="color:#93c5fd">"message"</span>: <span style="color:#86efac">"Envio processado com sucesso"</span>,
  <span style="color:#93c5fd">"data"</span>: {
    <span style="color:#93c5fd">"amount"</span>: <span style="color:#fde68a">5000</span>,
    <span style="color:#93c5fd">"fee"</span>: <span style="color:#fde68a">50</span>,
    <span style="color:#93c5fd">"sent"</span>: <span style="color:#fde68a">4950</span>,
    <span style="color:#93c5fd">"destination"</span>: <span style="color:#86efac">"cliente@email.com"</span>
  }
}`}</CodeBlock>
      </Grid2>
    </div>
  )
}
