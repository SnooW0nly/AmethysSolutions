'use client'

import { DocPageHeader, EndpointBar } from '@/components/docs/doc-components'

export default function AfiliadosEstatisticasPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <DocPageHeader
        badge="Afiliados"
        title="Estatísticas de afiliado"
        description="Retorna estatísticas detalhadas: lista de indicados, transações de cada um e comissões por período."
      />

      <EndpointBar method="GET" path="/affiliate/stats" auth />

      <p className="text-[14px] text-foreground/50 leading-relaxed">
        Este endpoint retorna um relatório completo com todos os usuários indicados, o volume de transações de cada um e
        o total de comissões geradas. Ideal para dashboards de afiliados.
      </p>
    </div>
  )
}
