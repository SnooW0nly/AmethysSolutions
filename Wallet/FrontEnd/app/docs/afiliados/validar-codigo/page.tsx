'use client'

import { DocPageHeader, EndpointBar, CodeBlock, Grid2 } from '@/components/docs/doc-components'

export default function AfiliadosValidarCodigoPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <DocPageHeader
        badge="Afiliados"
        title="Validar código de afiliado"
        description="Verifica se um código de afiliado é válido. Endpoint público — não requer autenticação. Use durante o cadastro de novos usuários."
      />

      <EndpointBar method="GET" path="/affiliate/validate/:code" />

      <Grid2>
        <CodeBlock lang="request">{`curl https://api.amethys.lat/api/v1/affiliate/validate/joaosilva`}</CodeBlock>
        <CodeBlock lang="response 200" copyable={false}>{`<span style="color:#71717a">// Válido:</span>
{
  <span style="color:#93c5fd">"valid"</span>: <span style="color:#f0abfc">true</span>,
  <span style="color:#93c5fd">"data"</span>: {
    <span style="color:#93c5fd">"code"</span>: <span style="color:#86efac">"joaosilva"</span>,
    <span style="color:#93c5fd">"name"</span>: <span style="color:#86efac">"João"</span>
  }
}

<span style="color:#71717a">// Inválido:</span>
{
  <span style="color:#93c5fd">"valid"</span>: <span style="color:#f0abfc">false</span>,
  <span style="color:#93c5fd">"error"</span>: <span style="color:#86efac">"Código não encontrado"</span>
}`}</CodeBlock>
      </Grid2>
    </div>
  )
}
