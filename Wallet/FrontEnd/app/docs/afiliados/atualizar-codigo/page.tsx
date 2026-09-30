'use client'

import { DocPageHeader, EndpointBar, ParamsTable } from '@/components/docs/doc-components'

export default function AfiliadosAtualizarCodigoPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <DocPageHeader
        badge="Afiliados"
        title="Atualizar código de afiliado"
        description="Altera o código de afiliado. O link de indicação é atualizado imediatamente."
      />

      <EndpointBar method="PUT" path="/affiliate/code" auth />

      <ParamsTable params={[
        { name: 'code', type: 'string', required: true, description: 'Novo código (3–30 chars, letras, números, - e _)' },
      ]} />
    </div>
  )
}
