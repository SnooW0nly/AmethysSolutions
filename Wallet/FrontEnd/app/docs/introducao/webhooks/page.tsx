'use client'

import { DocPageHeader, CodeBlock, Callout } from '@/components/docs/doc-components'

const events = [
  { event: 'payment.completed', trigger: 'PIX recebido e creditado na conta' },
  { event: 'payment.refunded', trigger: 'Envio de PIX processado' },
  { event: 'withdraw.completed', trigger: 'Saque concluído com sucesso' },
  { event: 'withdraw.failed', trigger: 'Saque falhou' },
]

export default function WebhooksPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <DocPageHeader
        badge="Introdução"
        title="Webhooks"
        description="Configure uma URL de webhook ao registrar ou atualizar sua conta. A Amethys enviará eventos em tempo real para sua URL quando pagamentos forem confirmados ou saques processados."
      />

      <div className="mb-8">
        <h2 className="text-[17px] font-semibold text-foreground mb-4">Eventos disponíveis</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-[13px] border-collapse">
            <thead>
              <tr className="border-b border-foreground/10">
                {['Evento', 'Gatilho'].map(col => (
                  <th key={col} className="text-left py-2.5 px-3 text-[10px] font-semibold text-foreground/30 uppercase tracking-wider font-mono">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {events.map(({ event, trigger }) => (
                <tr key={event} className="border-b border-foreground/[0.06] last:border-0 hover:bg-foreground/[0.02]">
                  <td className="py-3 px-3 font-mono text-[12px] text-primary">{event}</td>
                  <td className="py-3 px-3 text-foreground/50">{trigger}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mb-8">
        <h2 className="text-[17px] font-semibold text-foreground mb-4">Payload do webhook</h2>
        <CodeBlock lang="json">{`{
  <span style="color:#93c5fd">"event"</span>: <span style="color:#86efac">"payment.completed"</span>,
  <span style="color:#93c5fd">"txid"</span>: <span style="color:#86efac">"pix_abc123xyz"</span>,
  <span style="color:#93c5fd">"amount"</span>: <span style="color:#86efac">"100.00"</span>,
  <span style="color:#93c5fd">"netAmount"</span>: <span style="color:#86efac">"99.50"</span>,
  <span style="color:#93c5fd">"status"</span>: <span style="color:#86efac">"completed"</span>,
  <span style="color:#93c5fd">"paidAt"</span>: <span style="color:#fde68a">1716700000</span>
}`}</CodeBlock>
      </div>

      <Callout type="info">
        Sua URL de webhook deve responder com <strong>HTTP 200</strong> em até 5 segundos.
        Configure em <code className="font-mono text-[12px] text-primary">PUT /user/update</code> com o campo <code className="font-mono text-[12px] text-primary">webhookUrl</code>.
      </Callout>
    </div>
  )
}
