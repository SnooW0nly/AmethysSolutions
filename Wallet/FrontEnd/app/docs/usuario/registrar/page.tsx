'use client'

import { DocPageHeader, EndpointBar, ParamsTable, CodeBlock, Grid2 } from '@/components/docs/doc-components'

export default function UsuarioRegistrarPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <DocPageHeader
        badge="Usuário"
        title="Registrar usuário"
        description="Cria uma nova conta na Amethys Wallet e retorna a API Key gerada. Guarde-a com segurança — não é possível recuperá-la."
      />

      <EndpointBar method="POST" path="/user/register" />

      <div className="mb-6">
        <h3 className="text-[13px] font-semibold text-foreground/60 uppercase tracking-wider mb-3 font-mono">Parâmetros do body</h3>
        <ParamsTable params={[
          { name: 'name', type: 'string', required: true, description: 'Nome completo do titular' },
          { name: 'email', type: 'string', required: true, description: 'E-mail único da conta' },
          { name: 'pixKey', type: 'string', required: true, description: 'Chave PIX para saques automáticos' },
          { name: 'pixKeyType', type: 'string', required: true, description: <><code className="font-mono text-[11px] text-primary">CPF</code>, <code className="font-mono text-[11px] text-primary">CNPJ</code>, <code className="font-mono text-[11px] text-primary">EMAIL</code>, <code className="font-mono text-[11px] text-primary">PHONE</code> ou <code className="font-mono text-[11px] text-primary">RANDOM</code></> },
          { name: 'taxID', type: 'string', required: false, description: 'CPF ou CNPJ sem pontuação' },
          { name: 'phone', type: 'string', required: false, description: 'Telefone com DDD' },
          { name: 'webhookUrl', type: 'string', required: false, description: 'URL HTTPS para receber eventos' },
        ]} />
      </div>

      <Grid2>
        <CodeBlock lang="request">{`curl -X POST https://api.amethys.lat/api/v1/user/register \\
  -H <span style="color:#86efac">"Content-Type: application/json"</span> \\
  -d '{
    <span style="color:#93c5fd">"name"</span>: <span style="color:#86efac">"João Silva"</span>,
    <span style="color:#93c5fd">"email"</span>: <span style="color:#86efac">"joao@empresa.com"</span>,
    <span style="color:#93c5fd">"pixKey"</span>: <span style="color:#86efac">"joao@empresa.com"</span>,
    <span style="color:#93c5fd">"pixKeyType"</span>: <span style="color:#86efac">"EMAIL"</span>,
    <span style="color:#93c5fd">"taxID"</span>: <span style="color:#86efac">"12345678901"</span>,
    <span style="color:#93c5fd">"webhookUrl"</span>: <span style="color:#86efac">"https://meusite.com/webhook"</span>
  }'`}</CodeBlock>
        <CodeBlock lang="response 201" copyable={false}>{`{
  <span style="color:#93c5fd">"success"</span>: <span style="color:#f0abfc">true</span>,
  <span style="color:#93c5fd">"message"</span>: <span style="color:#86efac">"Usuário registrado com sucesso"</span>,
  <span style="color:#93c5fd">"data"</span>: {
    <span style="color:#93c5fd">"id"</span>: <span style="color:#86efac">"reg_abc123"</span>,
    <span style="color:#93c5fd">"apiKey"</span>: <span style="color:#86efac">"vp_xxxxxxxxxxxxxxxxxxx"</span>,
    <span style="color:#93c5fd">"name"</span>: <span style="color:#86efac">"João Silva"</span>,
    <span style="color:#93c5fd">"email"</span>: <span style="color:#86efac">"joao@empresa.com"</span>,
    <span style="color:#93c5fd">"pixKey"</span>: <span style="color:#86efac">"joao@empresa.com"</span>,
    <span style="color:#93c5fd">"pixKeyType"</span>: <span style="color:#86efac">"EMAIL"</span>,
    <span style="color:#93c5fd">"balance"</span>: <span style="color:#fde68a">0</span>,
    <span style="color:#93c5fd">"paymentFee"</span>: <span style="color:#fde68a">50</span>,
    <span style="color:#93c5fd">"message"</span>: <span style="color:#86efac">"Guarde sua API Key em local seguro!"</span>
  }
}`}</CodeBlock>
      </Grid2>
    </div>
  )
}
