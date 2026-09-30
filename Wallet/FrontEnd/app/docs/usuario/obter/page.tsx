'use client'

import { DocPageHeader, EndpointBar, CodeBlock } from '@/components/docs/doc-components'

export default function UsuarioObterPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <DocPageHeader
        badge="Usuário"
        title="Obter dados do usuário"
        description="Retorna os dados do usuário autenticado, incluindo plano, limites e chave PIX."
      />

      <EndpointBar method="GET" path="/user/get" auth />

      <CodeBlock lang="response 200" copyable={false}>{`{
  <span style="color:#93c5fd">"success"</span>: <span style="color:#f0abfc">true</span>,
  <span style="color:#93c5fd">"data"</span>: {
    <span style="color:#93c5fd">"id"</span>: <span style="color:#86efac">"reg_abc123"</span>,
    <span style="color:#93c5fd">"name"</span>: <span style="color:#86efac">"João Silva"</span>,
    <span style="color:#93c5fd">"email"</span>: <span style="color:#86efac">"joao@empresa.com"</span>,
    <span style="color:#93c5fd">"balance"</span>: <span style="color:#fde68a">15000</span>,
    <span style="color:#93c5fd">"status"</span>: <span style="color:#86efac">"active"</span>,
    <span style="color:#93c5fd">"pixKey"</span>: <span style="color:#86efac">"joao@empresa.com"</span>,
    <span style="color:#93c5fd">"pixKeyType"</span>: <span style="color:#86efac">"EMAIL"</span>,
    <span style="color:#93c5fd">"plan"</span>: {
      <span style="color:#93c5fd">"name"</span>: <span style="color:#86efac">"FREE"</span>,
      <span style="color:#93c5fd">"transactionFee"</span>: <span style="color:#fde68a">50</span>,
      <span style="color:#93c5fd">"transactionFeeInReais"</span>: <span style="color:#86efac">"0.50"</span>,
      <span style="color:#93c5fd">"monthlyFee"</span>: <span style="color:#fde68a">0</span>
    },
    <span style="color:#93c5fd">"planDates"</span>: {
      <span style="color:#93c5fd">"endDate"</span>: <span style="color:#f0abfc">null</span>,
      <span style="color:#93c5fd">"daysRemaining"</span>: <span style="color:#f0abfc">null</span>,
      <span style="color:#93c5fd">"autoRenew"</span>: <span style="color:#f0abfc">true</span>
    },
    <span style="color:#93c5fd">"limits"</span>: {
      <span style="color:#93c5fd">"perTransaction"</span>: <span style="color:#fde68a">100000</span>
    },
    <span style="color:#93c5fd">"createdAt"</span>: <span style="color:#86efac">"2025-05-01T12:00:00.000Z"</span>
  }
}`}</CodeBlock>
    </div>
  )
}
