'use client'

import { DocPageHeader, EndpointBar, ParamsTable } from '@/components/docs/doc-components'

export default function AfiliadosRegistrarPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <DocPageHeader
        badge="Afiliados"
        title="Registrar como afiliado"
        description="Cria um perfil de afiliado para a conta autenticada com um código personalizado ou gerado automaticamente."
      />

      <EndpointBar method="POST" path="/affiliate/register" auth />

      <ParamsTable params={[
        { name: 'code', type: 'string', required: false, description: 'Código de afiliado personalizado (3–30 chars, apenas letras, números, - e _). Se omitido, é gerado automaticamente.' },
      ]} />
    </div>
  )
}
