'use client'

import { DocPageHeader, EndpointBar, CodeBlock } from '@/components/docs/doc-components'

export default function AfiliadosMeusDadosPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <DocPageHeader
        badge="Afiliados"
        title="Meus dados de afiliado"
        description="Retorna dados do perfil de afiliado: código, link, total de indicações e comissões acumuladas."
      />

      <EndpointBar method="GET" path="/affiliate/me" auth />

      <CodeBlock lang="response 200" copyable={false}>{`{
  <span style="color:#93c5fd">"success"</span>: <span style="color:#f0abfc">true</span>,
  <span style="color:#93c5fd">"isAffiliate"</span>: <span style="color:#f0abfc">true</span>,
  <span style="color:#93c5fd">"data"</span>: {
    <span style="color:#93c5fd">"id"</span>: <span style="color:#86efac">"aff_abc"</span>,
    <span style="color:#93c5fd">"code"</span>: <span style="color:#86efac">"joaosilva"</span>,
    <span style="color:#93c5fd">"link"</span>: <span style="color:#86efac">"https://amethys.lat/joaosilva"</span>,
    <span style="color:#93c5fd">"totalReferrals"</span>: <span style="color:#fde68a">12</span>,
    <span style="color:#93c5fd">"totalEarnings"</span>: <span style="color:#fde68a">3500</span>,
    <span style="color:#93c5fd">"totalEarningsInReais"</span>: <span style="color:#86efac">"35.00"</span>,
    <span style="color:#93c5fd">"commissionPerTransaction"</span>: <span style="color:#fde68a">5</span>,
    <span style="color:#93c5fd">"status"</span>: <span style="color:#86efac">"active"</span>,
    <span style="color:#93c5fd">"createdAt"</span>: <span style="color:#86efac">"2025-04-01T00:00:00.000Z"</span>
  }
}`}</CodeBlock>
    </div>
  )
}
