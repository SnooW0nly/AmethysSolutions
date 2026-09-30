'use client'

import { DocPageHeader, EndpointBar, ParamsTable, CodeBlock, Grid2 } from '@/components/docs/doc-components'

export default function SaquesPixPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <DocPageHeader
        badge="Saques"
        title="Sacar via PIX"
        description="Saque imediato via PIX para qualquer chave. Mínimo de R$ 5,00. Apenas um saque pode estar em processamento por vez."
      />

      <EndpointBar method="POST" path="/withdraw/create" auth />

      <div className="mb-6">
        <h3 className="text-[13px] font-semibold text-foreground/60 uppercase tracking-wider mb-3 font-mono">Parâmetros do body</h3>
        <ParamsTable params={[
          { name: 'amount', type: 'number', required: true, description: 'Valor em reais. Mínimo: R$ 5,00' },
          { name: 'pixKey', type: 'string', required: true, description: 'Chave PIX de destino' },
          { name: 'pixKeyType', type: 'string', required: true, description: <><code className="font-mono text-[11px] text-primary">CPF</code>, <code className="font-mono text-[11px] text-primary">CNPJ</code>, <code className="font-mono text-[11px] text-primary">EMAIL</code>, <code className="font-mono text-[11px] text-primary">PHONE</code>, <code className="font-mono text-[11px] text-primary">RANDOM</code></> },
          { name: 'description', type: 'string', required: false, description: 'Descrição do saque' },
          { name: 'coverFee', type: 'boolean', required: false, description: <>Se <code className="font-mono text-[11px] text-primary">true</code>, o valor informado é o líquido que o destinatário recebe</> },
          { name: 'verificationCode', type: 'string', required: false, description: 'Código de segurança (se transferência segura estiver ativa)' },
          { name: 'splitUser', type: 'string', required: false, description: 'E-mail para dividir o saque' },
          { name: 'splitTax', type: 'number', required: false, description: 'Porcentagem para o splitUser (0.01–100)' },
        ]} />
      </div>

      <Grid2>
        <CodeBlock lang="request">{`curl -X POST https://api.amethys.lat/api/v1/withdraw/create \\
  -H <span style="color:#86efac">"X-API-Key: vp_sua_key"</span> \\
  -H <span style="color:#86efac">"Content-Type: application/json"</span> \\
  -d '{
    <span style="color:#93c5fd">"amount"</span>: <span style="color:#fde68a">200</span>,
    <span style="color:#93c5fd">"pixKey"</span>: <span style="color:#86efac">"minha@conta.com"</span>,
    <span style="color:#93c5fd">"pixKeyType"</span>: <span style="color:#86efac">"EMAIL"</span>,
    <span style="color:#93c5fd">"description"</span>: <span style="color:#86efac">"Saque semanal"</span>
  }'`}</CodeBlock>
        <CodeBlock lang="response 201" copyable={false}>{`{
  <span style="color:#93c5fd">"success"</span>: <span style="color:#f0abfc">true</span>,
  <span style="color:#93c5fd">"message"</span>: <span style="color:#86efac">"Saque processado com sucesso"</span>,
  <span style="color:#93c5fd">"data"</span>: {
    <span style="color:#93c5fd">"id"</span>: <span style="color:#86efac">"wdr_abc456"</span>,
    <span style="color:#93c5fd">"value"</span>: <span style="color:#fde68a">20000</span>,
    <span style="color:#93c5fd">"fee"</span>: <span style="color:#fde68a">50</span>,
    <span style="color:#93c5fd">"sent"</span>: <span style="color:#fde68a">19950</span>,
    <span style="color:#93c5fd">"pixKey"</span>: <span style="color:#86efac">"minha@conta.com"</span>,
    <span style="color:#93c5fd">"status"</span>: <span style="color:#86efac">"PROCESSING"</span>,
    <span style="color:#93c5fd">"createdAt"</span>: <span style="color:#86efac">"2025-05-14T11:00:00.000Z"</span>
  }
}`}</CodeBlock>
      </Grid2>
    </div>
  )
}
