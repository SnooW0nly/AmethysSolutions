'use client'

import { DocPageHeader, EndpointBar, CodeBlock } from '@/components/docs/doc-components'

export default function UsuarioSaldoPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <DocPageHeader
        badge="Usuário"
        title="Consultar saldo"
        description="Retorna o saldo atual da conta, estatísticas de pagamentos, limites e informações do plano."
      />

      <EndpointBar method="GET" path="/user/balance" auth />

      <CodeBlock lang="response 200" copyable={false}>{`{
  <span style="color:#93c5fd">"success"</span>: <span style="color:#f0abfc">true</span>,
  <span style="color:#93c5fd">"data"</span>: {
    <span style="color:#93c5fd">"balance"</span>: {
      <span style="color:#93c5fd">"total"</span>: <span style="color:#fde68a">15000</span>,          <span style="color:#71717a">// R$ 150,00 em centavos</span>
      <span style="color:#93c5fd">"pendingPayments"</span>: <span style="color:#fde68a">2000</span>,  <span style="color:#71717a">// cobranças aguardando pagamento</span>
      <span style="color:#93c5fd">"totalWithPending"</span>: <span style="color:#fde68a">17000</span>,
      <span style="color:#93c5fd">"isNegative"</span>: <span style="color:#f0abfc">false</span>
    },
    <span style="color:#93c5fd">"statistics"</span>: {
      <span style="color:#93c5fd">"totalReceived"</span>: <span style="color:#fde68a">50000</span>,
      <span style="color:#93c5fd">"totalFees"</span>: <span style="color:#fde68a">250</span>,
      <span style="color:#93c5fd">"completedPayments"</span>: <span style="color:#fde68a">5</span>,
      <span style="color:#93c5fd">"pendingPayments"</span>: <span style="color:#fde68a">2</span>
    },
    <span style="color:#93c5fd">"limits"</span>: {
      <span style="color:#93c5fd">"perTransaction"</span>: <span style="color:#fde68a">100000</span>
    },
    <span style="color:#93c5fd">"plan"</span>: {
      <span style="color:#93c5fd">"name"</span>: <span style="color:#86efac">"FREE"</span>,
      <span style="color:#93c5fd">"transactionFee"</span>: <span style="color:#fde68a">50</span>,
      <span style="color:#93c5fd">"transactionFeeInReais"</span>: <span style="color:#86efac">"R$ 0,50"</span>
    }
  }
}`}</CodeBlock>
    </div>
  )
}
